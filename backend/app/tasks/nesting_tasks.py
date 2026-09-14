"""
非同步裁切排版任務 — 用於大量零件、複雜混單排版時，避免阻塞API回應
小量零件（<50個）建議走同步 /api/v1/nesting/calculate 端點

⚠️ 現況說明（v1.9稽核記錄）：這兩個task目前尚未被router或其他模組實際呼叫，
   屬於預留給未來大量訂單場景的基礎設施。稽核時發現並修正兩個問題：
   1. celery_app.py 的 autodiscover_tasks(["app.tasks"]) 命名慣例不符
      （見celery_app.py註解），導致這裡的task從未被worker真正註冊過。
   2. 本檔案 calculate_nesting_async 直接用 Part(**p) 建構，若呼叫端傳入的
      parts_data缺少label欄位會直接TypeError崩潰；已補上預設值處理。
"""
from app.tasks.celery_app import celery_app
from app.ai.nesting_bfd import BFDNestingEngine, Part

@celery_app.task(name="nesting.calculate_async", bind=True)
def calculate_nesting_async(self, sheet_length: float, sheet_width: float,
                             kerf: float, parts_data: list[dict]):
    """
    大量訂單混單排版的非同步任務
    parts_data: [{"id": "...", "length": ..., "width": ..., "quantity": ..., "can_rotate": ...}]
    label 為選填，若caller未提供則沿用id作為顯示標籤
    """
    engine = BFDNestingEngine(sheet_length, sheet_width, kerf)
    parts = [Part(**{**p, "label": p.get("label", p["id"])}) for p in parts_data]
    result = engine.nest(parts)
    return result

@celery_app.task(name="nesting.batch_optimize")
def batch_optimize_multiple_orders(order_ids: list[str]):
    """
    跨工單混排：將多筆訂單的相同材質零件合併排版以提升利用率
    實際邏輯：查詢各工單BOM → 依material_id分組 → 呼叫nesting engine → 回寫nesting_jobs
    """
    # TODO: 串接資料庫查詢邏輯（需在Celery worker中建立獨立DB session）
    return {"status": "pending_implementation", "order_count": len(order_ids)}
