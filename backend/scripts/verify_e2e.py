"""
端到端驗證腳本：真實 HTTP request 打真實 PostgreSQL，不做靜態推論。

涵蓋：官網詢價 → 後台檢視 → 轉客戶；BOM 展開 → 工單 → 發料扣庫存
（含庫存不足整批擋下）→ MES 報工 → 完工入庫 FG 倉。

執行前提：後端已啟動、資料庫已 migrate 並 seed。

    cd backend
    alembic upgrade head
    python scripts/seed_data.py
    uvicorn app.main:app --port 8000 &
    python scripts/verify_e2e.py            # 預設打 http://127.0.0.1:8000
    API_BASE=http://localhost:8000 python scripts/verify_e2e.py

任一項失敗時以 exit code 1 結束，可直接用於 CI。
"""
import json
import sys
import urllib.request
import urllib.error

import os
import uuid as _uuid
BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
RUN = _uuid.uuid4().hex[:6]  # 每次執行用不同代號，避免 unique 欄位撞到前一輪殘留資料
TOKEN = None
FAILS = []


def call(method, path, body=None, auth=True, expect=200):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if auth and TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req) as r:
            status, payload = r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = {"raw": raw.decode(errors="replace")[:500]}
        status = e.code
    ok = status == expect
    mark = "PASS" if ok else "FAIL"
    if not ok:
        FAILS.append(f"{method} {path} -> {status} (expected {expect}): {payload}")
    print(f"[{mark}] {method} {path} -> {status}")
    return payload


print("=" * 70)
print("1. 登入")
r = call("POST", "/api/v1/auth/login",
         {"email": "admin@guishan-acrylic.com", "password": "ChangeMe123!"}, auth=False)
TOKEN = r["access_token"]

print("\n2. 官網詢價（公開端點，無需登入）")
inq = call("POST", "/api/v1/public/inquiries", {
    "name": "王大明", "company": "美妝通路股份有限公司",
    "email": "wang@example.com", "phone": "0912-345-678",
    "product_type": "彩妝展示架", "quantity": "約120台",
    "description": "壓克力+LED，高60cm，需含品牌雷雕",
}, auth=False)
inq_id = inq["inquiry_id"]

print("\n3. 後台讀得到剛才那筆詢價（前後端確實串接）")
lst = call("GET", "/api/v1/inquiries")
found = [i for i in lst["data"] if i["id"] == inq_id]
assert found and found[0]["name"] == "王大明", "後台沒讀到官網送出的詢價"
print(f"      → 詢價內容確實落庫：{found[0]['company']} / {found[0]['quantity']}")

print("\n4. 詢價轉正式客戶")
conv = call("POST", f"/api/v1/inquiries/{inq_id}/convert-to-customer")
cust_id = conv["customer_id"]
print(f"      → {conv['message']}")
conv2 = call("POST", f"/api/v1/inquiries/{inq_id}/convert-to-customer")
assert conv2["already_converted"] is True, "重複轉換應為冪等，不得重建客戶"
print("      → 重複呼叫為冪等，未重複建立客戶")

print("\n5. 建立物料 / 產品 / BOM")
mat = call("POST", "/api/v1/materials", {
    "code": f"AC-T3-{RUN}", "name": "透明壓克力3mm", "material_type": "acrylic",
    "thickness_mm": 3, "color": "transparent", "unit": "才",
    "unit_cost": 145, "cost_per_sqm": 145, "min_stock_qty": 10,
})
mat_id = mat["data"]["id"] if "data" in mat else mat["material_id"]

prod = call("POST", "/api/v1/products", {
    "sku": f"DSP-MK-{RUN}", "name": "彩妝展示架A型", "product_type": "custom",
    "category": "彩妝架", "unit": "台", "list_price": 3800,
})
prod_id = prod["data"]["id"] if "data" in prod else prod["product_id"]

bom = call("POST", "/api/v1/bom", {
    "product_id": prod_id,
    "items": [{"line_no": 1, "material_id": mat_id, "quantity": 2,
               "unit": "才", "wastage_rate": 0.1}],
})
bom_id = bom.get("bom_id") or bom["data"]["id"]
call("POST", f"/api/v1/bom/{bom_id}/approve")

print("\n6. 建立工單（數量10 → 備料需求 2*10*1.1 = 22才）")
wo = call("POST", "/api/v1/work-orders", {
    "product_id": prod_id, "bom_id": bom_id, "quantity": 10, "priority": 3,
    "operations": [{"op_seq": 1, "op_name": "CNC裁切", "run_time_per_unit_min": 3},
                   {"op_seq": 2, "op_name": "組裝", "run_time_per_unit_min": 5}],
})
wo_id = wo["wo_id"]
plan = call("GET", f"/api/v1/work-orders/{wo_id}/material-plan")
need = plan["data"][0]["planned_qty"]
print(f"      → 備料需求 {need} 才（BOM 2才 × 10台 × 1.1損耗）")
assert abs(need - 22.0) < 0.001, f"備料計算錯誤：{need}"

call("POST", f"/api/v1/work-orders/{wo_id}/release")

print("\n7. 庫存不足時，發料必須整批擋下（不可部分發料）")
call("POST", "/api/v1/inventory/receipt", {
    "material_id": mat_id, "warehouse_code": "RAW", "qty": 5,
    "unit_cost": 145, "source_type": "MANUAL",
})
short = call("POST", f"/api/v1/work-orders/{wo_id}/issue-materials",
             {"warehouse_code": "RAW"}, expect=409)
det = short.get("detail", {})
print(f"      → 正確擋下：缺 {det.get('shortages', [{}])[0].get('shortage_qty')} 才")
bal = call("GET", "/api/v1/inventory/balance?warehouse_code=RAW")
raw_after_reject = [b for b in bal["data"] if b["material_id"] == mat_id][0]["qty_on_hand"]
assert abs(raw_after_reject - 5.0) < 0.001, f"被拒絕的發料不該動到庫存，實際={raw_after_reject}"
print(f"      → 被拒絕後庫存仍為 {raw_after_reject} 才，未被部分扣帳")

print("\n8. 補足庫存後發料，庫存確實扣減")
call("POST", "/api/v1/inventory/receipt", {
    "material_id": mat_id, "warehouse_code": "RAW", "qty": 20,
    "unit_cost": 145, "source_type": "MANUAL",
})
issued = call("POST", f"/api/v1/work-orders/{wo_id}/issue-materials", {"warehouse_code": "RAW"})
print(f"      → {issued['message']}")
bal = call("GET", "/api/v1/inventory/balance?warehouse_code=RAW")
raw_after = [b for b in bal["data"] if b["material_id"] == mat_id][0]["qty_on_hand"]
print(f"      → RAW庫存 25 - 22 = {raw_after} 才")
assert abs(raw_after - 3.0) < 0.001, f"發料後庫存錯誤：{raw_after}"

print("\n9. 工序未完成時，完工入庫必須被擋下")
call("POST", f"/api/v1/work-orders/{wo_id}/complete", {}, expect=400)
print("      → 正確擋下（尚有工序未完成）")

print("\n10. MES報工完成兩道工序")
detail = call("GET", f"/api/v1/work-orders/{wo_id}")
for op in detail["data"]["operations"]:
    call("POST", f"/api/v1/work-orders/{wo_id}/operations/{op['id']}/start")
    call("POST", f"/api/v1/work-orders/{wo_id}/operations/{op['id']}/complete",
         {"good_qty": 9, "scrap_qty": 1})

print("\n11. 完工入庫 → 成品進FG倉")
done = call("POST", f"/api/v1/work-orders/{wo_id}/complete", {})
print(f"      → {done['message']}")
assert done["data"]["received_qty"] == 9, "應取最後一道工序良品數9，而非各工序加總"
fg = call("GET", "/api/v1/inventory/balance?warehouse_code=FG")
fg_rows = [b for b in fg["data"] if b.get("product_id") == prod_id]
assert fg_rows and abs(fg_rows[0]["qty_on_hand"] - 9.0) < 0.001, f"FG庫存錯誤：{fg['data']}"
print(f"      → FG倉成品庫存 = {fg_rows[0]['qty_on_hand']} 台")

print("\n12. 重複入庫必須被擋下")
call("POST", f"/api/v1/work-orders/{wo_id}/complete", {}, expect=400)
print("      → 正確擋下（工單已完工）")

print("\n13. 官網公開作品API")
call("GET", "/api/v1/public/portfolio", auth=False)

print("\n" + "=" * 70)
if FAILS:
    print(f"❌ {len(FAILS)} 項失敗：")
    for f in FAILS:
        print("   " + f)
    sys.exit(1)
print("✅ 全部 v2.0 新功能端到端驗證通過")
