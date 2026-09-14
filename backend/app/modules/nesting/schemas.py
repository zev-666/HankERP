from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class PartInput(BaseModel):
    label: str = Field(..., description="零件名稱，例如：正面板")
    length_mm: Decimal = Field(..., ge=10, description="長度mm")
    width_mm: Decimal = Field(..., ge=10, description="寬度mm")
    quantity: int = Field(1, ge=1)
    can_rotate: bool = True
    bom_item_id: Optional[UUID] = None

class NestingRequest(BaseModel):
    material_id: UUID
    wo_id: Optional[UUID] = None
    sheet_length_mm: Decimal = Field(2000, description="原板長度mm")
    sheet_width_mm: Decimal = Field(1000, description="原板寬度mm")
    kerf_mm: Decimal = Field(3, description="刀縫寬度mm")
    parts: List[PartInput] = Field(..., min_length=1)

class PlacementOut(BaseModel):
    part_label: str
    sheet_index: int
    x_mm: float
    y_mm: float
    placed_length: float
    placed_width: float
    rotated: bool

class NestingResultOut(BaseModel):
    job_id: UUID
    status: str
    sheets_used: Optional[int]
    utilization_rate: Optional[float]
    waste_area_mm2: Optional[float]
    placements: Optional[List[PlacementOut]]
    remnants: Optional[List[dict]]
    created_at: datetime
    class Config: from_attributes = True


class PresetCompareRequest(BaseModel):
    """比較9種板型，僅計算不寫入資料庫"""
    kerf_mm: Decimal = Field(3, description="刀縫寬度mm")
    parts: List[PartInput] = Field(..., min_length=1)


class PresetCompareItem(BaseModel):
    name: str
    sheet_length: float
    sheet_width: float
    sheets_used: Optional[int]
    utilization_rate: float
    impossible: bool


class PresetCompareResponse(BaseModel):
    items: List[PresetCompareItem]
    best_preset: Optional[str]
    best_sheets_used: Optional[int]
    best_utilization_rate: Optional[float]
