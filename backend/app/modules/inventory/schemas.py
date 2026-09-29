from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class InventoryBalanceOut(BaseModel):
    id: UUID
    # v2.2：對齊 models/inventory.py。v2.0 已把 material_id 改為可空並新增
    # product_id（成品庫存存在 FG 倉，成品屬 products 主檔而非 materials），
    # 但這個 schema 一直沒跟著改。目前 /balance 端點沒有設 response_model，
    # 所以還沒爆；只要有人補上 response_model=，FG 倉的每一筆
    # （material_id 為 NULL）都會直接 500。
    material_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    warehouse_code: str
    location_code: Optional[str]
    qty_on_hand: Decimal
    qty_reserved: Decimal
    qty_available: Decimal
    last_updated: datetime
    class Config: from_attributes = True

class TransactionCreate(BaseModel):
    material_id: UUID
    warehouse_code: str = "RAW"
    qty: Decimal = Field(..., description="正=入庫 負=出庫")
    unit_cost: Optional[Decimal] = None
    source_type: Optional[str] = None
    source_id: Optional[UUID] = None
    lot_number: Optional[str] = None
    notes: Optional[str] = None

class TransactionOut(BaseModel):
    id: int
    transaction_type: str
    material_id: UUID
    warehouse_code: str
    qty: Decimal
    unit_cost: Optional[Decimal]
    created_at: datetime
    class Config: from_attributes = True

class SheetStockCreate(BaseModel):
    material_id: UUID
    batch_no: Optional[str] = None
    actual_length_mm: Decimal = Field(2000, ge=10)
    actual_width_mm: Decimal = Field(1000, ge=10)
    quantity: int = Field(1, ge=1)
    location_code: Optional[str] = None

class SheetStockOut(BaseModel):
    id: UUID
    material_id: UUID
    batch_no: Optional[str]
    actual_length_mm: Decimal
    actual_width_mm: Decimal
    quantity: int
    is_remnant: bool
    remnant_grade: Optional[str]
    status: str
    created_at: datetime
    class Config: from_attributes = True

class RemnantCreate(BaseModel):
    material_id: UUID
    length_mm: Decimal = Field(..., ge=50, description="最小50mm")
    width_mm: Decimal = Field(..., ge=50)
    grade: str = "A"
    location_code: Optional[str] = None
    notes: Optional[str] = None
    nesting_job_id: Optional[UUID] = None
