"""
RBAC 執行層的真實 HTTP 驗證（v2.2）。

為什麼需要這支
--------------
`tests/test_permissions.py` 驗的是「權限表對不對」，是純資料檢查。
但表對不代表有生效——本專案歷史上最常見的問題正是「寫了但沒接上」。
這支腳本用真實 HTTP request 打真實資料庫：建立 9 個角色各一個帳號，
逐一登入，實際去撞該撞的牆。

**在 v2.2 之前的程式碼上執行，這支必定失敗**，因為當時沒有任何端點
檢查權限，所有「應為 403」的案例都會回 200。這就是它抓得到問題的證明。

執行前提：後端已啟動、資料庫已 migrate 並 seed。

    API_BASE=http://127.0.0.1:8000 python scripts/verify_rbac.py

需要環境變數 SEED_ADMIN_PASSWORD（與 seed_data.py 同一組）。
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid as _uuid

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "admin@guishan-acrylic.com")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD") or os.environ.get("SEED_ADMIN_PASSWORD")
RUN = _uuid.uuid4().hex[:8]
# 這批測試帳號的密碼只存在於本次執行的記憶體中，不寫死也不列印。
TEST_PASSWORD = _uuid.uuid4().hex + "A1"

ROLE_NAMES = ["admin", "owner", "sales", "engineer", "planner",
              "warehouse", "purchaser", "operator", "qc"]

FAILS: list[str] = []


def call(method, path, body=None, token=None):
    """回傳 (status, payload)。不做任何斷言。"""
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return e.code, {"raw": raw.decode(errors="replace")[:300]}


def expect(condition, label, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}")
    if not condition:
        if detail:
            print(f"       {detail}")
        FAILS.append(label)


# ── 0. 前置 ──────────────────────────────────────────────────────────
if not ADMIN_PASSWORD:
    print("✗ 未設定 SEED_ADMIN_PASSWORD（或 E2E_ADMIN_PASSWORD）")
    sys.exit(1)

print("=" * 70)
print("0. 管理員登入")
status, payload = call("POST", "/api/v1/auth/login",
                       {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
if status != 200:
    print(f"✗ 管理員登入失敗：{status} {payload}")
    sys.exit(1)
admin_token = payload["access_token"]
expect(payload.get("role") == "admin", "登入回應帶出真實角色名 admin",
       f"實際：{payload.get('role')!r}")

# ── 1. 提權漏洞：未登入不得自行註冊帳號 ──────────────────────────────
print("\n1. 公開自助註冊已關閉（v2.2 前任何人都能把自己註冊成 admin）")
evil_email = f"escalation-{RUN}@example.com"
status, payload = call("POST", "/api/v1/auth/register", {
    "email": evil_email, "password": TEST_PASSWORD,
    "full_name": "提權測試", "role_name": "admin",
})
expect(status in (401, 403),
       f"未帶 token 呼叫 /auth/register 應被擋下（實際 {status}）",
       f"回應：{payload}")
if status == 200:
    print(f"       ⚠ 嚴重：已實際建立出一個 admin 帳號 {evil_email}，請立刻刪除！")

# ── 2. 以管理員身分建立 9 個角色的測試帳號 ───────────────────────────
print("\n2. 管理員建立各角色測試帳號")
tokens: dict[str, str] = {}
for role in ROLE_NAMES:
    email = f"rbac-{role}-{RUN}@example.com"
    status, payload = call("POST", "/api/v1/auth/register", {
        "email": email, "password": TEST_PASSWORD,
        "full_name": f"RBAC測試-{role}", "role_name": role,
    }, token=admin_token)
    if status != 200:
        expect(False, f"建立 {role} 帳號", f"{status} {payload}")
        continue
    status, payload = call("POST", "/api/v1/auth/login",
                           {"email": email, "password": TEST_PASSWORD})
    if status != 200:
        expect(False, f"{role} 登入", f"{status} {payload}")
        continue
    tokens[role] = payload["access_token"]
    expect(payload.get("role") == role, f"{role} 帳號建立並登入成功",
           f"回傳角色為 {payload.get('role')!r}")

if len(tokens) != len(ROLE_NAMES):
    print("\n✗ 測試帳號未能全數建立，後續判斷無意義，中止。")
    sys.exit(1)

# ── 3. 權限邊界（只用 GET，不產生副作用）────────────────────────────
# (角色, method, 路徑, 應否放行)
# 「應放行」= 非 401/403；「應擋下」= 剛好 403。
CASES = [
    # 廠長唯讀 ＋ 可看分析
    ("owner", "GET", "/api/v1/analytics/dashboard", True),
    ("owner", "GET", "/api/v1/customers", True),

    # 業務要報價就得讀得到 BOM 與庫存（v2.2 補上，否則報價功能會壞）
    ("sales", "GET", "/api/v1/customers", True),
    ("sales", "GET", "/api/v1/materials", True),
    ("sales", "GET", "/api/v1/inventory/balance", True),
    ("sales", "GET", "/api/v1/analytics/cost-breakdown", False),

    # 工程師管產品與裁切，碰不到客戶
    ("engineer", "GET", "/api/v1/materials", True),
    ("engineer", "GET", "/api/v1/nesting/jobs", True),
    ("engineer", "GET", "/api/v1/customers", False),

    # 生管管工單，也能算裁切（v2.2 補上）
    ("planner", "GET", "/api/v1/work-orders", True),
    ("planner", "GET", "/api/v1/nesting/jobs", True),
    ("planner", "GET", "/api/v1/customers", False),

    # 倉管管庫存，看得到採購單但碰不到分析
    ("warehouse", "GET", "/api/v1/inventory/balance", True),
    ("warehouse", "GET", "/api/v1/purchase-orders", True),
    ("warehouse", "GET", "/api/v1/analytics/dashboard", False),

    # 採購只管採購
    ("purchaser", "GET", "/api/v1/purchase-orders", True),
    ("purchaser", "GET", "/api/v1/work-orders", False),

    # 作業員只能看工單報工，其餘全擋
    ("operator", "GET", "/api/v1/work-orders", True),
    ("operator", "GET", "/api/v1/inventory/balance", False),
    ("operator", "GET", "/api/v1/analytics/dashboard", False),
    ("operator", "GET", "/api/v1/customers", False),

    # 品管看得到工單與庫存，看不到報價
    ("qc", "GET", "/api/v1/work-orders", True),
    ("qc", "GET", "/api/v1/inventory/balance", True),
    ("qc", "GET", "/api/v1/quotations", False),
]

print("\n3. 各角色權限邊界（真實 HTTP）")
for role, method, path, allowed in CASES:
    status, payload = call(method, path, token=tokens[role])
    if allowed:
        ok = status not in (401, 403)
        expect(ok, f"{role:10} {method} {path} → 應放行（{status}）", f"回應：{payload}")
    else:
        ok = status == 403
        expect(ok, f"{role:10} {method} {path} → 應 403（{status}）", f"回應：{payload}")

# ── 4. 只有管理員能開帳號 ────────────────────────────────────────────
print("\n4. 非管理員不得建立帳號")
for role in ("owner", "sales", "operator"):
    status, payload = call("POST", "/api/v1/auth/register", {
        # 刻意給不存在的角色：萬一權限沒生效而真的執行到，也會卡在角色查無，
        # 不會真的建出帳號；而 400 與 403 正好能區分「有沒有被擋」。
        "email": f"nope-{role}-{RUN}@example.com", "password": TEST_PASSWORD,
        "full_name": "不該被建立", "role_name": "__no_such_role__",
    }, token=tokens[role])
    expect(status == 403, f"{role:10} POST /api/v1/auth/register → 應 403（{status}）",
           f"回應：{payload}（400 代表權限未生效，請求已進到業務邏輯）")

# ── 5. 未登入不得存取業務端點；公開端點不受影響 ──────────────────────
print("\n5. 未登入的邊界")
status, _ = call("GET", "/api/v1/customers")
expect(status == 401, f"未登入 GET /api/v1/customers → 應 401（{status}）")
status, _ = call("GET", "/health")
expect(status == 200, f"未登入 GET /health → 應 200（{status}）")
status, _ = call("GET", "/api/v1/public/portfolio")
expect(status in (200, 429), f"未登入 GET /api/v1/public/portfolio → 應 200（{status}）")

# ── 結果 ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"測試帳號後綴：{RUN}（如需清理：DELETE FROM users WHERE email LIKE '%-{RUN}@example.com';）")
if FAILS:
    print(f"❌ {len(FAILS)} 項失敗：")
    for f in FAILS:
        print("   " + f)
    sys.exit(1)
print("✅ RBAC 執行層驗證通過：9 種角色的權限邊界皆符合權限矩陣")
