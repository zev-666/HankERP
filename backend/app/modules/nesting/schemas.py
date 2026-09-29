from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Literal, Optional, List
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
    # v2.3：預設板改為 S 1915×1315——本廠的標準板。
    # 先前寫 2000×1000，那是舊文件的錯誤值（2000×1000 只是 9 種板型之一）。
    sheet_length_mm: Decimal = Field(1915, description="原板長度mm（預設 S 板 1915）")
    sheet_width_mm: Decimal = Field(1315, description="原板寬度mm（預設 S 板 1315）")
    kerf_mm: Decimal = Field(3, description="刀縫寬度mm")
    # v2.3 新增（開條引擎專用）
    trim_mm: Decimal = Field(0, ge=0, le=200, description="四邊修邊mm，0=板邊直接當基準邊")
    rem_pref: Literal["any", "strip", "long"] = Field(
        "any", description="剩料取向：any=兩個開條方向都試；strip=強制沿短邊；long=強制沿長邊")
    min_remnant_mm: Decimal = Field(
        50, ge=0, description="可回收剩料的最小邊長mm（NEEDS_FACTORY_VERIFICATION：50 是否合理未經工廠確認）")
    max_sheets: int = Field(0, ge=0, description="0=依需求算需要幾張；>0=我有固定張數，算最多裁幾件")
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
    trim_mm: Decimal = Field(0, ge=0, le=200, description="四邊修邊mm")
    rem_pref: Literal["any", "strip", "long"] = Field("any", description="剩料取向")
    min_remnant_mm: Decimal = Field(50, ge=0, description="可回收剩料最小邊長mm")
    parts: List[PartInput] = Field(..., min_length=1)


class PresetCompareItem(BaseModel):
    name: str
    sheet_length: float
    sheet_width: float
    sheets_used: Optional[int]
    utilization_rate: float
    # 總才數＝張數 × 單張才數，是實際要買的材料量，比利用率更能反映成本
    total_cai: Optional[float] = None
    band_remnant_cai: float = 0.0
    total_cuts: Optional[int] = None
    unplaced_count: Optional[int] = None
    impossible: bool


class PresetCompareResponse(BaseModel):
    engine: str
    items: List[PresetCompareItem]
    best_preset: Optional[str]
    best_sheets_used: Optional[int]
    best_utilization_rate: Optional[float]
    best_total_cai: Optional[float] = None
