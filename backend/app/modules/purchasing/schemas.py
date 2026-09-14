from uuid import UUID
from decimal import Decimal
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field

class PoItemCreate(BaseModel):
    material_id: UUID
    ordered_qty: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    unit: str = "片"
    sheet_thickness_mm: Optional[Decimal] = None
    sheet_length_mm: Optional[Decimal] = None
    sheet_width_mm: Optional[Decimal] = None
    sheet_color: Optional[str] = None
    notes: Optional[str] = None

class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    expected_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[PoItemCreate] = Field(..., min_length=1)

class ReceiveItemIn(BaseModel):
    po_item_id: UUID
    received_qty: Decimal = Field(..., gt=0)
    actual_length_mm: Optional[Decimal] = None
    actual_width_mm: Optional[Decimal] = None
    batch_no: Optional[str] = None
    quality_notes: Optional[str] = None
