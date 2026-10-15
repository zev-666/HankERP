"""
專打「建 BOM → 建工單 → 查備料清單」這段序列的重現腳本（v2.3.2）。

為什麼需要它
------------
CI #5、#6、#8 三次失敗都是同一個家族：**前一個請求寫入成功，下一個請求讀不到**。
- CI #5：兩道工序都報工完成，`complete` 卻說「尚有工序未完成」
- CI #6：`complete` 回 200「完工入庫 9 件」，下一個 request 查 FG 倉卻是空的
- CI #8：工單建立回 200，`material-plan` 回傳空陣列

每次都只在 CI 出現、本機跑三次重現不出來、同一個 commit 重跑就綠。
全套 `verify_e2e.py` 跑一輪要好幾秒，撞到的機率太低。

這支只做最短的那段序列，一輪不到 1 秒，可以連跑幾十上百次，
並且在每一輪都**回讀 bom_items**，把問題切成兩段：

    建 BOM → 回讀 bom_items → 建工單 → 查 material-plan
             ↑ 這裡是 0？          ↑ 還是這裡是 0？

前者代表 BOM 明細沒落庫（寫入端問題），後者代表工單展不開（讀取端問題）。
兩者的修法完全不同，不先分清楚就是在猜。

用法
----
    docker compose exec backend python scripts/repro_bom_wo.py           # 預設 50 輪
    docker compose exec backend python scripts/repro_bom_wo.py 200       # 跑 200 輪

需要環境變數 SEED_ADMIN_PASSWORD（與 seed_data.py 同一組）。
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
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 50
# 第二個參數：每個請求之間的延遲（毫秒）。用來驗證失敗是不是交易時序造成的：
# 0 會重現，拉大到 300 就全過 → 寫入有落庫，只是 commit 比下一個請求晚。
DELAY_MS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0

TOKEN = None


def call(method, path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req) as r:
            out = r.status, json.loads(r.read() or b"{}")
        if DELAY_MS:
            time.sleep(DELAY_MS / 1000.0)
        return out
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return e.code, {"raw": raw.decode(errors="replace")[:300]}


def login():
    global TOKEN
    import time
    for _ in range(8):
        st, p = call("POST", "/api/v1/auth/login",
                     {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        if st == 200:
            TOKEN = p["access_token"]
            return True
        if st != 429:
            print(f"X 登入失敗 {st}: {p}")
            return False
        time.sleep(13)   # /auth/login 限流 5/minute，等待重試而不是放寬限流
    return False


def one_round(i):
    """回傳 (ok, 診斷字串)。"""
    run = _uuid.uuid4().hex[:8]

    st, mat = call("POST", "/api/v1/materials", {
        "code": f"RP-{run}", "name": "重現用料", "material_type": "acrylic",
        "thickness_mm": 3, "color": "transparent", "unit": "才",
        "unit_cost": 145, "min_stock_qty": 10,
    })
    if st != 200:
        return False, f"建立物料失敗 {st}: {mat}"
    mat_id = (mat.get("data") or {}).get("id") or mat.get("material_id")

    st, prod = call("POST", "/api/v1/products", {
        "sku": f"RP-{run}", "name": "重現用產品", "product_type": "custom",
        "category": "測試", "unit": "台", "list_price": 1000,
    })
    if st != 200:
        return False, f"建立產品失敗 {st}: {prod}"
    prod_id = (prod.get("data") or {}).get("id") or prod.get("product_id")

    st, bom = call("POST", "/api/v1/bom", {
        "product_id": prod_id,
        "items": [{"line_no": 1, "material_id": mat_id, "quantity": 2,
                   "unit": "才", "wastage_rate": 0.1}],
    })
    if st != 200:
        return False, f"建立 BOM 失敗 {st}: {bom}"
    bom_id = bom.get("bom_id") or (bom.get("data") or {}).get("id")

    # -- 切點 1：BOM 明細有沒有真的落庫？ --
    st, exp = call("GET", f"/api/v1/bom/{bom_id}/expand")
    items_back = (exp.get("items") or []) if st == 200 else []
    if st != 200 or len(items_back) != 1:
        return False, (f"【寫入端】BOM 明細回讀異常：status={st} 筆數={len(items_back)}\n"
                       f"          bom_id={bom_id}\n"
                       f"          回應={exp}")

    st, wo = call("POST", "/api/v1/work-orders", {
        "product_id": prod_id, "bom_id": bom_id, "quantity": 10, "priority": 3,
        "operations": [{"op_seq": 1, "op_name": "CNC裁切", "run_time_per_unit_min": 3}],
    })
    if st != 200:
        # v2.3.2 起，展不出備料明細會在這裡 400 並說明原因
        return False, f"【建立工單】status={st}\n          回應={wo}"
    wo_id = wo["wo_id"]

    # -- 切點 2：工單展不展得開？ --
    st, plan = call("GET", f"/api/v1/work-orders/{wo_id}/material-plan")
    rows = (plan.get("data") or []) if st == 200 else []
    if st != 200 or not rows:
        return False, (f"【讀取端】備料清單為空：status={st}\n"
                       f"          wo_id={wo_id}  bom_id={bom_id}\n"
                       f"          bom_items 回讀筆數={len(items_back)}（上一步確認過是 1）\n"
                       f"          material-plan 回應={plan}\n"
                       f"          建立工單回應={wo}")

    need = rows[0]["planned_qty"]
    if abs(float(need) - 22.0) > 0.001:
        return False, f"備料數量錯誤：{need}（預期 22.0）"
    return True, ""


def empty_bom_check():
    """v2.3.2：BOM 沒有任何明細時，建立工單必須回 400，而不是靜默建立。"""
    run = _uuid.uuid4().hex[:8]
    st, prod = call("POST", "/api/v1/products", {
        "sku": f"RP-E-{run}", "name": "重現用產品（空BOM）", "product_type": "custom",
        "category": "測試", "unit": "台", "list_price": 1000,
    })
    if st != 200:
        return False, f"建立產品失敗 {st}: {prod}"
    prod_id = prod.get("product_id")
    st, bom = call("POST", "/api/v1/bom", {"product_id": prod_id, "items": []})
    if st != 200:
        return False, f"建立空 BOM 失敗 {st}: {bom}"
    st, wo = call("POST", "/api/v1/work-orders", {
        "product_id": prod_id, "bom_id": bom["bom_id"], "quantity": 10, "priority": 3,
        "operations": [],
    })
    detail = wo.get("detail") if isinstance(wo, dict) else None
    if st == 400 and isinstance(detail, dict) and detail.get("bom_header_found") is True:
        return True, ""
    return False, f"空 BOM 建工單應回 400（bom_header_found=True），實際 status={st} 回應={wo}"


def main():
    if not ADMIN_PASSWORD:
        print("X 未設定 SEED_ADMIN_PASSWORD（或 E2E_ADMIN_PASSWORD）")
        return 1
    if not login():
        return 1

    print(f"連跑 {ROUNDS} 輪，請求間隔 {DELAY_MS:.0f} ms："
          "建料 → 建產品 → 建 BOM → 回讀明細 → 建工單 → 查備料")
    print("=" * 70)
    fails = []
    for i in range(1, ROUNDS + 1):
        ok, detail = one_round(i)
        if ok:
            print(".", end="", flush=True)
        else:
            print("X", flush=True)
            print(f"\n--- 第 {i} 輪失敗 ---\n{detail}\n")
            fails.append(i)
        if i % 50 == 0:
            print(f"  [{i}]", flush=True)

    print("\n" + "=" * 70)
    ok, detail = empty_bom_check()
    print(("[OK] " if ok else "[FAIL] ") + "空 BOM 建工單 → 400" + ("" if ok else f"\n   {detail}"))
    if not ok:
        fails.append("empty-bom")
    if fails:
        print(f"[FAIL] {ROUNDS} 輪中有 {len(fails)} 輪失敗：第 {fails} 輪")
        print("   把上面的失敗明細整段貼回來——【寫入端】和【讀取端】決定了修法完全不同。")
        return 1
    print(f"[OK] {ROUNDS} 輪全部通過，這一輪沒有重現")
    print("   重現不到不代表問題不存在（CI 上是偶發的）。可以加大輪數再試，")
    print("   例如：docker compose exec backend python scripts/repro_bom_wo.py 300")
    return 0


if __name__ == "__main__":
    sys.exit(main())
