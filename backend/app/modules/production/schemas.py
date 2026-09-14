from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field

class WoOperationCreate(BaseModel):
    op_seq: int
    op_name: str  # 'CNC裁切','雷射雕刻','噴漆','組裝','包裝'
    machine_id: Optional[UUID] = None
    setup_time_min: int = 0
    run_time_per_unit_min: Decimal = Decimal("0")

class WorkOrderCreate(BaseModel):
    product_id: UUID
    bom_id: Optional[UUID] = None
    quantity: int = Field(..., ge=1)
    priority: int = Field(5, ge=1, le=10)
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    notes: Optional[str] = None
    operations: List[WoOperationCreate] = []

class WorkOrderOut(BaseModel):
    id: UUID
    wo_number: str
    product_id: UUID
    quantity: int
    status: str
    priority: int
    planned_start: Optional[date]
    planned_end: Optional[date]
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    created_at: datetime
    class Config: from_attributes = True

class OperationReportIn(BaseModel):
    good_qty: int = 0
    scrap_qty: int = 0
    notes: Optional[str] = None


class MaterialIssueIn(BaseModel):
    """工單發料。warehouse_code 預設 RAW＝原料倉。"""
    warehouse_code: str = "RAW"


class WorkOrderCompleteIn(BaseModel):
    """
    工單完工入庫。
    good_qty 留空時由後端取最後一道工序的良品數，避免前端誤把各工序良品數加總。
    """
    good_qty: Optional[int] = Field(default=None, ge=1)
    warehouse_code: str = "FG"
