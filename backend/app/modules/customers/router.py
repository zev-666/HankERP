from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.modules.customers.service import CustomerService
from app.modules.customers.schemas import (
    CustomerCreate, CustomerUpdate, CustomerOut, ActivityCreate
)

router = APIRouter(prefix="/api/v1/customers", tags=["客戶管理 CRM"])
svc = CustomerService()

@router.get("", summary="客戶列表")
async def list_customers(
    search: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customers = await svc.list_customers(db, current_user.tenant_id, search, industry, tier, skip, limit)
    return {"success": True, "data": customers, "total": len(customers)}

@router.post("", summary="新增客戶")
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = await svc.create_customer(db, current_user.tenant_id, current_user.id, data)
    return {"success": True, "customer_id": str(c.id), "code": c.code}

@router.get("/{customer_id}", summary="客戶詳情")
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = await svc.get_customer(db, current_user.tenant_id, customer_id)
    if not c:
        raise HTTPException(404, "找不到此客戶")
    return {"success": True, "data": c}

@router.get("/{customer_id}/360", summary="客戶360視圖（基本資料+互動記錄+報價歷史）")
async def get_customer_360(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await svc.get_customer_360(db, current_user.tenant_id, customer_id)
    if not result:
        raise HTTPException(404, "找不到此客戶")
    return {"success": True, "data": {
        "customer": result["customer"],
        "activities": result["activities"],
        "quotations": result["quotations"],
        "total_quotes": result["total_quotes"],
        "won_quotes": result["won_quotes"],
        "win_rate_pct": round(result["won_quotes"] / result["total_quotes"] * 100, 1) if result["total_quotes"] > 0 else 0,
    }}

@router.put("/{customer_id}", summary="更新客戶資料")
async def update_customer(
    customer_id: UUID, data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = await svc.update_customer(db, current_user.tenant_id, customer_id, data)
    if not c:
        raise HTTPException(404, "找不到此客戶")
    return {"success": True, "message": "更新成功"}

@router.get("/{customer_id}/activities", summary="客戶互動記錄")
async def list_activities(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    acts = await svc.list_activities(db, customer_id)
    return {"success": True, "data": acts}

@router.post("/{customer_id}/activities", summary="新增互動記錄")
async def add_activity(
    customer_id: UUID, data: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    act = await svc.add_activity(db, customer_id, current_user.id, data)
    return {"success": True, "activity_id": str(act.id)}
