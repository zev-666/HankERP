from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field

class QuotationItemCreate(BaseModel):
    description: str
    quantity: int = 1
    product_id: Optional[UUID] = None
    # 壓克力計算輸入
    acrylic_cai: Optional[Decimal] = Field(None, description="預計用料（才）")
    cnc_minutes: Optional[Decimal] = None
    laser_meters: Optional[Decimal] = None
    assembly_hours: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None  # 若為None則AI自動計算

class QuotationCreate(BaseModel):
    customer_id: UUID
    valid_until: Optional[date] = None
    profit_margin: Decimal = Field(Decimal("0.35"), ge=0, le=0.9)
    notes: Optional[str] = None
    items: List[QuotationItemCreate]

class AIEstimateRequest(BaseModel):
    """快速AI估價輸入"""
    product_description: str
    acrylic_items: List[dict] = Field([], description="[{color,thickness_mm,length_mm,width_mm,qty}]")
    operations: List[dict] = Field([], description="[{type,estimated_minutes}]")
    quantity: int = 1
    target_margin: Optional[float] = 0.35

class QuotationOut(BaseModel):
    id: UUID
    quote_number: str
    customer_id: UUID
    status: str
    material_cost: Decimal
    processing_cost: Decimal
    overhead_cost: Decimal
    final_price: Decimal
    profit_margin: Decimal
    ai_generated: bool
    created_at: datetime
    class Config: from_attributes = True
