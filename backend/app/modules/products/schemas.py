from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field

class BomItemCreate(BaseModel):
    line_no: int
    material_id: UUID
    quantity: Decimal = Field(..., gt=0)
    unit: str = "片"
    wastage_rate: Decimal = Field(Decimal("0.05"), ge=0, le=1)
    cut_length_mm: Optional[Decimal] = None
    cut_width_mm: Optional[Decimal] = None
    notes: Optional[str] = None
    is_optional: bool = False
    substitute_material_id: Optional[UUID] = None

class BomCreate(BaseModel):
    product_id: UUID
    version: int = 1
    effective_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[BomItemCreate]

class BomItemOut(BomItemCreate):
    id: UUID
    class Config: from_attributes = True

class BomOut(BaseModel):
    id: UUID
    product_id: UUID
    version: int
    status: str
    effective_date: Optional[date]
    items: List[BomItemOut] = []
    created_at: datetime
    class Config: from_attributes = True

class ProductCreate(BaseModel):
    sku: str
    name: str
    name_en: Optional[str] = None
    product_type: str = "custom"
    category: Optional[str] = None
    description: Optional[str] = None
    list_price: Decimal = Decimal("0")
    unit: str = "台"
    lead_time_days: Optional[int] = None
    min_order_qty: int = 1

class ProductOut(BaseModel):
    id: UUID
    sku: str
    name: str
    product_type: str
    category: Optional[str]
    list_price: Decimal
    unit: str
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True

class MaterialCreate(BaseModel):
    code: Optional[str] = None
    name: str
    material_type: str   # acrylic/wood/metal/led/paint/hardware
    thickness_mm: Optional[Decimal] = None
    color: Optional[str] = None
    standard_length_mm: Decimal = Decimal("2000")
    standard_width_mm: Decimal = Decimal("1000")
    unit: str = "片"
    unit_cost: Decimal = Decimal("0")
    cost_per_cai: Optional[Decimal] = None
    min_stock_qty: Decimal = Decimal("0")
    reorder_point: Decimal = Decimal("0")

class MaterialOut(MaterialCreate):
    id: UUID
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True
