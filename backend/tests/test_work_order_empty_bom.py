"""
指定了 BOM 卻展不出備料明細時，建立工單必須失敗（v2.3.2）。

舊行為：create_work_order 查不到 bom_items 就默默跳過，工單照樣建立、
回 200，現場拿到一張沒有備料清單的工單。CI #8 就是倒在這裡，而且沒有任何
錯誤訊息。這支測試在舊程式上會失敗（DID NOT RAISE），已實際驗證過。

不需要資料庫：假 session 依 create_work_order 的呼叫順序回值。
"""
import asyncio
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.production.schemas import WorkOrderCreate  # noqa: E402
from app.modules.production.service import ProductionService  # noqa: E402


class _Result:
    def __init__(self, scalar=None, rows=None):
        self._scalar, self._rows = scalar, rows or []

    def scalar(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDB:
    """依序回應：工單流水號計數 → BOM 明細（空）→ BOM 主檔計數。"""

    def __init__(self, bom_header_count: int):
        self._results = [_Result(scalar=0), _Result(rows=[]), _Result(scalar=bom_header_count)]

    def add(self, obj):
        pass

    async def flush(self):
        pass

    async def execute(self, _stmt):
        return self._results.pop(0)


def _create(bom_header_count: int):
    data = WorkOrderCreate(
        product_id=uuid.uuid4(), bom_id=uuid.uuid4(), quantity=10, priority=3, operations=[],
    )
    return asyncio.run(ProductionService().create_work_order(
        FakeDB(bom_header_count), uuid.uuid4(), uuid.uuid4(), data,
    ))


@pytest.mark.parametrize("header_count,found,hint_kw", [
    (1, True, "沒有任何明細"),    # BOM 主檔在、明細是空的
    (0, False, "不存在"),         # bom_id 根本不存在
])
def test_empty_bom_blocks_work_order(header_count, found, hint_kw):
    with pytest.raises(Exception) as ei:
        _create(header_count)
    err = ei.value
    assert type(err).__name__ == "EmptyMaterialPlanError", f"丟出的是 {type(err).__name__}：{err}"
    assert err.detail["bom_header_found"] is found
    assert err.detail["bom_item_count"] == 0
    assert hint_kw in err.detail["hint"]
