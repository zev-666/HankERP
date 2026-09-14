from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from decimal import Decimal
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.equipment import Equipment, MaintenanceLog

router = APIRouter(prefix="/api/v1/equipment", tags=["設備管理"])

class EquipmentCreate(BaseModel):
    code: str
    name: str
    equipment_type: str  # cnc/laser/saw/spray/drill/polish
    model: Optional[str] = None
    hourly_rate: Decimal = Decimal("0")
    power_kw: Optional[Decimal] = None
    notes: Optional[str] = None

class MaintenanceCreate(BaseModel):
    maintenance_type: str  # preventive/corrective/inspection
    description: str
    technician: Optional[str] = None
    cost: Optional[Decimal] = None
    downtime_hours: Optional[Decimal] = None
    performed_at: datetime
    next_maintenance_date: Optional[str] = None

@router.post("", summary="新增設備")
async def create_equipment(
    data: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    eq = Equipment(
        tenant_id=current_user.tenant_id,
        code=data.code,
        name=data.name,
        equipment_type=data.equipment_type,
        model=data.model,
        hourly_rate=data.hourly_rate,
        power_kw=data.power_kw,
        notes=data.notes,
    )
    db.add(eq)
    await db.flush()
    return {"success": True, "equipment_id": str(eq.id), "message": f"設備 {data.name} 已建立"}

@router.get("", summary="設備清單")
async def list_equipment(
    equipment_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Equipment).where(Equipment.tenant_id == current_user.tenant_id)
    if equipment_type:
        q = q.where(Equipment.equipment_type == equipment_type)
    result = await db.execute(q)
    eqs = result.scalars().all()
    return {"success": True, "data": [
        {"id": str(e.id), "code": e.code, "name": e.name,
         "equipment_type": e.equipment_type, "status": e.status,
         "hourly_rate": float(e.hourly_rate)}
        for e in eqs
    ]}

@router.post("/{eq_id}/maintenance", summary="記錄保養/維修")
async def log_maintenance(
    eq_id: UUID,
    data: MaintenanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date
    log = MaintenanceLog(
        equipment_id=eq_id,
        maintenance_type=data.maintenance_type,
        description=data.description,
        technician=data.technician,
        cost=data.cost,
        downtime_hours=data.downtime_hours,
        performed_at=data.performed_at,
        next_maintenance_date=date.fromisoformat(data.next_maintenance_date) if data.next_maintenance_date else None,
        created_by=current_user.id,
    )
    db.add(log)
    # 若是corrective維修，更新設備狀態
    if data.maintenance_type == "corrective":
        q = select(Equipment).where(Equipment.id == eq_id)
        result = await db.execute(q)
        eq = result.scalar_one_or_none()
        if eq:
            eq.status = "active"  # 維修完成後復原
    await db.flush()
    return {"success": True, "message": "保養記錄已建立"}

@router.patch("/{eq_id}/status", summary="更新設備狀態")
async def update_status(
    eq_id: UUID,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed = {"active", "maintenance", "breakdown", "retired"}
    if status not in allowed:
        raise HTTPException(400, f"狀態必須是: {allowed}")
    q = select(Equipment).where(Equipment.id == eq_id,
                                 Equipment.tenant_id == current_user.tenant_id)
    result = await db.execute(q)
    eq = result.scalar_one_or_none()
    if not eq:
        raise HTTPException(404, "找不到設備")
    eq.status = status
    return {"success": True, "message": f"設備 {eq.name} 狀態更新為 {status}"}
