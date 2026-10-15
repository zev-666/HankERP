"""
AI 快速估價（POST /api/v1/quotations/ai-estimate）必須算出正確金額（v2.3.6）。

v2.0 起的三個 bug（2026-10-15 使用者回報「按計算報價沒反應」）：
1. 前端讀 final_price／material_cost 等欄位，後端實際回 total_price_twd／breakdown.material_cost_twd，
   結果框出現但數字全空。
2. 表單送的板材沒有 type="acrylic"，QuoteEngine.calc_acrylic_cost 全部跳過 → 材料成本永遠 0。
3. 表單送 qty，引擎讀 quantity → 片數被忽略，2 片只算 1 片。

本測試直接呼叫端點函式（不需資料庫），用前端實際送出的格式。已在舊程式上確認會失敗。
"""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.encoders import jsonable_encoder  # noqa: E402

import app.modules.quotation.router as q_router  # noqa: E402
from app.modules.quotation.schemas import AIEstimateRequest  # noqa: E402

# 前端 /erp/quotations「AI快速估價」預設值的實際送出格式
FRONTEND_PAYLOAD = {
    "product_description": "彩妝展示架",
    "acrylic_items": [{"color": "transparent", "thickness_mm": 3,
                       "length_mm": 500, "width_mm": 400, "qty": 2}],
    "operations": [{"type": "cnc_cut", "estimated_minutes": 30},
                   {"type": "assembly", "estimated_minutes": 60}],
    "quantity": 1,
}


def _estimate(payload: dict) -> dict:
    req = AIEstimateRequest(**payload)
    out = asyncio.run(q_router.ai_estimate(req, current_user=SimpleNamespace()))
    return jsonable_encoder(out)["estimate"]


def test_material_cost_counts_acrylic_and_piece_count():
    # 500×400×2 片 = 400,000 mm² ÷ 90,000 × 1.10 損耗 × 145（透明 3mm）= 708.89
    est = _estimate(FRONTEND_PAYLOAD)
    assert est["breakdown"]["material_cost_twd"] == pytest.approx(709, abs=1)


def test_total_price_matches_published_formula():
    # 加工 30×8 + 60×4 = 480；管銷 (708.89+480)×0.25；報價 ÷ (1−0.35)
    est = _estimate(FRONTEND_PAYLOAD)
    mat, proc = 708.888, 480.0
    expected = (mat + proc) * 1.25 / 0.65
    assert est["breakdown"]["processing_cost_twd"] == 480
    assert est["total_price_twd"] == pytest.approx(expected, abs=1)
    assert est["unit_price_twd"] == est["total_price_twd"]


def test_quantity_multiplies_total():
    one = _estimate(FRONTEND_PAYLOAD)
    ten = _estimate({**FRONTEND_PAYLOAD, "quantity": 10})
    assert ten["total_price_twd"] == pytest.approx(one["total_price_twd"] * 10, abs=10)
    assert ten["unit_price_twd"] == pytest.approx(one["unit_price_twd"], abs=1)


def test_frontend_reads_fields_the_api_returns():
    """前端顯示的四個數字，必須讀後端真的有回的欄位（防止再次對不上）。"""
    page = (Path(__file__).resolve().parents[2] / "frontend/src/app/erp/quotations/page.tsx")
    if not page.exists():
        pytest.skip("前端原始碼不在此執行環境（例如 backend 容器內）")
    src = page.read_text(encoding="utf-8")
    est = _estimate(FRONTEND_PAYLOAD)
    for path in ("breakdown.material_cost_twd", "breakdown.processing_cost_twd",
                 "total_price_twd", "unit_price_twd"):
        node = est
        for k in path.split("."):
            node = node[k]
        assert path.split(".")[-1] in src, f"前端沒有讀 {path}"
    for stale in ("aiResult.final_price", "aiResult.material_cost?", "aiResult.unit_price?"):
        assert stale not in src, f"前端還在讀不存在的欄位 {stale}"
