"""
/api/v1/inventory/balance 必須回傳 qty_available（v2.3.3）。

舊行為：端點直接回傳 ORM 物件，qty_available 是模型上的 @property，
FastAPI 轉 JSON 時不會帶出來，前端「可用量」整欄空白。
本測試直接呼叫端點函式、再用 FastAPI 的 jsonable_encoder 轉成 JSON，
與實際回應走同一條序列化路徑，不需要資料庫。已在舊程式上確認會失敗。
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.encoders import jsonable_encoder  # noqa: E402

import app.modules.inventory.router as inv_router  # noqa: E402
from app.models.inventory import InventoryBalance  # noqa: E402


def _rows():
    tenant = uuid.uuid4()
    raw = InventoryBalance(id=uuid.uuid4(), tenant_id=tenant, material_id=uuid.uuid4(), product_id=None,
                           warehouse_code="RAW", qty_on_hand=Decimal("25"), qty_reserved=Decimal("4.5"),
                           last_updated=datetime.now(timezone.utc))
    fg = InventoryBalance(id=uuid.uuid4(), tenant_id=tenant, material_id=None, product_id=uuid.uuid4(),
                          warehouse_code="FG", qty_on_hand=Decimal("9"), qty_reserved=Decimal("0"),
                          last_updated=datetime.now(timezone.utc))
    return [raw, fg]


def _call(monkeypatch):
    rows = _rows()

    async def fake_get_balances(*_a, **_k):
        return rows

    monkeypatch.setattr(inv_router.svc, "get_balances", fake_get_balances)
    user = SimpleNamespace(tenant_id=rows[0].tenant_id)
    result = asyncio.run(inv_router.get_balances(None, None, db=None, current_user=user))
    return jsonable_encoder(result)


def test_balance_includes_qty_available(monkeypatch):
    data = _call(monkeypatch)["data"]
    raw, fg = data
    assert "qty_available" in raw, f"回應缺少 qty_available：{sorted(raw)}"
    assert raw["qty_available"] == 20.5
    assert fg["qty_available"] == 9.0


def test_balance_keeps_existing_field_types(monkeypatch):
    """verify_e2e.py 對 qty_on_hand 做數值運算、以字串比對 material_id／product_id。"""
    raw, fg = _call(monkeypatch)["data"]
    assert isinstance(raw["qty_on_hand"], (int, float)) and raw["qty_on_hand"] == 25
    assert isinstance(raw["material_id"], str) and raw["product_id"] is None
    assert fg["material_id"] is None and isinstance(fg["product_id"], str)
