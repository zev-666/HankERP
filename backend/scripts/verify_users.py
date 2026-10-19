"""
帳號管理的真實 HTTP 驗證（v2.3.8）。

用真實 HTTP request 打真實資料庫，走完管理員日常會做的事：
建員工帳號 → 改角色 → 員工忘記密碼由管理員重設 → 員工自己改密碼 → 離職停用。
同時檢查不該發生的事：非管理員碰帳號管理、管理員把自己停用或降級、
回應裡出現密碼雜湊、停用後舊的登入狀態還能用。

**在 v2.3.7 以前的程式碼上執行必定失敗**：當時沒有 /auth/me、/auth/users、
/auth/roles、改角色、停用、重設密碼這些端點（預設拒絕 → 403 或 404）。

執行前提：後端已啟動、資料庫已 migrate 並 seed。

    API_BASE=http://127.0.0.1:8000 python scripts/verify_users.py

需要環境變數 SEED_ADMIN_PASSWORD（與 seed_data.py 同一組）。
會留下 2 個已停用的測試帳號（verify-users-*@example.com），不影響正式使用者。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid as _uuid

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "admin@guishan-acrylic.com")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD") or os.environ.get("SEED_ADMIN_PASSWORD")
RUN = _uuid.uuid4().hex[:8]
# 測試帳號密碼只存在於本次執行的記憶體中，不寫死也不列印。
PW1 = _uuid.uuid4().hex + "A1"
PW2 = _uuid.uuid4().hex + "B2"
PW3 = _uuid.uuid4().hex + "C3"

FAILS: list[str] = []


def call(method, path, body=None, token=None):
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


def login(email, password, attempts=8, wait=13):
    """登入；遇到 429（登入限流 5/minute）等待重試，不放寬限流。"""
    for i in range(attempts):
        status, payload = call("POST", "/api/v1/auth/login", {"email": email, "password": password})
        if status != 429:
            return status, payload
        if i == 0:
            print("       （登入限流 5/minute，等待重試中…）")
        time.sleep(wait)
    return status, payload


def check(name, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        FAILS.append(f"{name} {detail}".strip())


def no_secrets(payload) -> bool:
    text = json.dumps(payload, ensure_ascii=False)
    return "hashed_password" not in text and "$2b$" not in text


if not ADMIN_PASSWORD:
    print("❌ 需要環境變數 SEED_ADMIN_PASSWORD（或 E2E_ADMIN_PASSWORD）")
    sys.exit(2)

print(f"帳號管理驗證（API {BASE}，本次代號 {RUN}）")

s, p = login(ADMIN_EMAIL, ADMIN_PASSWORD)
check("管理員登入", s == 200, f"{s} {p}")
if s != 200:
    sys.exit(1)
admin = p["access_token"]

# ── 1. 自己的資料、角色清單、帳號清單 ──
s, p = call("GET", "/api/v1/auth/me", token=admin)
me = p.get("data") or {}
check("GET /auth/me 回自己的資料", s == 200 and me.get("email") == ADMIN_EMAIL and me.get("role_name") == "admin", f"{s} {p}")
admin_id = me.get("id")

s, p = call("GET", "/api/v1/auth/roles", token=admin)
roles = {r.get("name"): r.get("display_name") for r in (p.get("data") or [])}
check("GET /auth/roles 回 9 種角色與中文名稱", s == 200 and len(roles) == 9 and roles.get("sales") == "業務/報價專員", f"{s} {roles}")

# ── 2. 建員工帳號 ──
staff_email = f"verify-users-{RUN}@example.com"
s, p = call("POST", "/api/v1/auth/register",
            {"email": staff_email, "password": PW1, "full_name": f"測試業務 {RUN}", "role_name": "sales"}, token=admin)
check("建立業務帳號", s == 200, f"{s} {p}")

s, p = call("POST", "/api/v1/auth/register",
            {"email": staff_email, "password": PW1, "full_name": "重複", "role_name": "sales"}, token=admin)
check("同一個 Email 不能建第二次 → 400", s == 400, f"{s} {p}")

s, p = call("POST", "/api/v1/auth/register",
            {"email": f"verify-users-weak-{RUN}@example.com", "password": "short", "full_name": "弱", "role_name": "sales"}, token=admin)
check("太弱的密碼 → 422", s == 422, f"{s}")

s, p = call("GET", "/api/v1/auth/users", token=admin)
users = p.get("data") or []
staff = next((u for u in users if u.get("email") == staff_email), None)
check("帳號清單看得到新員工，角色為業務、狀態啟用",
      s == 200 and staff is not None and staff.get("role_name") == "sales" and staff.get("is_active") is True, f"{s} {staff}")
check("帳號清單不含任何密碼雜湊", no_secrets(p))
staff_id = (staff or {}).get("id")
if not staff_id:
    print("❌ 找不到新員工，無法繼續")
    sys.exit(1)

# ── 3. 員工登入；不能碰帳號管理 ──
s, p = login(staff_email, PW1)
check("新員工可以登入，登入回應帶角色", s == 200 and p.get("role") == "sales", f"{s} {p}")
staff_token = p.get("access_token")

s, p = call("GET", "/api/v1/auth/me", token=staff_token)
check("員工看得到自己的資料", s == 200 and (p.get("data") or {}).get("email") == staff_email, f"{s} {p}")
check("員工的 /auth/me 不含密碼雜湊", no_secrets(p))
for method, path, body in [
    ("GET", "/api/v1/auth/users", None),
    ("GET", "/api/v1/auth/roles", None),
    ("PATCH", f"/api/v1/auth/users/{staff_id}", {"role_name": "admin"}),
    ("POST", f"/api/v1/auth/users/{admin_id}/reset-password", {"new_password": PW3}),
    ("POST", "/api/v1/auth/register", {"email": f"x-{RUN}@example.com", "password": PW3, "full_name": "x", "role_name": "admin"}),
]:
    s, p = call(method, path, body, token=staff_token)
    check(f"員工不能 {method} {path.replace(str(staff_id), '{員工}').replace(str(admin_id), '{管理員}')} → 403", s == 403, f"{s} {p}")

s, p = call("GET", "/api/v1/auth/users", token=admin)
staff_after = next((u for u in (p.get("data") or []) if u.get("id") == staff_id), {})
check("登入後記錄最後登入時間", bool(staff_after.get("last_login")), f"{staff_after}")

# ── 4. 管理員改角色、改名字 ──
s, p = call("PATCH", f"/api/v1/auth/users/{staff_id}", {"role_name": "planner", "full_name": f"改名生管 {RUN}"}, token=admin)
check("管理員把員工改成生管、改名字", s == 200 and (p.get("data") or {}).get("role_name") == "planner"
      and (p.get("data") or {}).get("full_name") == f"改名生管 {RUN}", f"{s} {p}")
s, p = call("PATCH", f"/api/v1/auth/users/{staff_id}", {"role_name": "no-such-role"}, token=admin)
check("改成不存在的角色 → 400", s == 400, f"{s} {p}")
s, p = call("GET", "/api/v1/nesting/jobs", token=staff_token)
check("改成生管後，同一個登入狀態馬上有生管權限（裁切）", s == 200, f"{s} {p}")

# ── 5. 員工忘記密碼：管理員重設 ──
s, p = call("POST", f"/api/v1/auth/users/{staff_id}/reset-password", {"new_password": PW2}, token=admin)
check("管理員重設員工密碼", s == 200, f"{s} {p}")
s, p = call("POST", f"/api/v1/auth/users/{staff_id}/reset-password", {"new_password": "short"}, token=admin)
check("重設成太弱的密碼 → 422", s == 422, f"{s}")
s, _ = login(staff_email, PW1)
check("舊密碼不能再登入 → 401", s == 401, f"{s}")
s, p = login(staff_email, PW2)
check("新密碼可以登入", s == 200, f"{s} {p}")
staff_token = p.get("access_token", staff_token)

# ── 6. 員工自己改密碼 ──
s, p = call("POST", "/api/v1/auth/change-password", {"old_password": PW1, "new_password": PW3}, token=staff_token)
check("舊密碼打錯不能改 → 400", s == 400, f"{s} {p}")
s, p = call("POST", "/api/v1/auth/change-password", {"old_password": PW2, "new_password": PW3}, token=staff_token)
check("員工自己改密碼", s == 200, f"{s} {p}")
s, _ = login(staff_email, PW3)
check("用自己改的新密碼登入", s == 200, f"{s}")

# ── 7. 管理員不能把自己鎖在外面 ──
s, p = call("PATCH", f"/api/v1/auth/users/{admin_id}", {"is_active": False}, token=admin)
check("管理員不能停用自己 → 400", s == 400, f"{s} {p}")
s, p = call("PATCH", f"/api/v1/auth/users/{admin_id}", {"role_name": "sales"}, token=admin)
check("管理員不能把自己降級 → 400", s == 400, f"{s} {p}")
s, p = call("POST", f"/api/v1/auth/users/{admin_id}/reset-password", {"new_password": PW3}, token=admin)
check("管理員重設自己密碼要走「變更密碼」（需要舊密碼）→ 400", s == 400, f"{s} {p}")
s, p = call("PATCH", f"/api/v1/auth/users/{admin_id}", {"full_name": "系統管理員"}, token=admin)
check("管理員可以改自己的顯示名稱", s == 200, f"{s} {p}")
s, p = call("PATCH", f"/api/v1/auth/users/{_uuid.uuid4()}", {"is_active": False}, token=admin)
check("不存在的帳號 → 404", s == 404, f"{s} {p}")

# ── 8. 停用（離職）：立刻失效 ──
s, p = call("PATCH", f"/api/v1/auth/users/{staff_id}", {"is_active": False}, token=admin)
check("停用員工帳號", s == 200 and (p.get("data") or {}).get("is_active") is False, f"{s} {p}")
s, p = call("GET", "/api/v1/auth/me", token=staff_token)
check("停用後，員工手上的登入狀態立刻失效 → 401", s == 401, f"{s} {p}")
s, _ = login(staff_email, PW3)
check("停用後不能再登入 → 401", s == 401, f"{s}")
s, p = call("PATCH", f"/api/v1/auth/users/{staff_id}", {"is_active": True}, token=admin)
check("可以重新啟用", s == 200 and (p.get("data") or {}).get("is_active") is True, f"{s} {p}")
call("PATCH", f"/api/v1/auth/users/{staff_id}", {"is_active": False}, token=admin)  # 收尾：保持停用

print()
if FAILS:
    print(f"❌ {len(FAILS)} 項失敗：")
    for f in FAILS:
        print("   " + f)
    sys.exit(1)
print("✅ 帳號管理驗證通過")
