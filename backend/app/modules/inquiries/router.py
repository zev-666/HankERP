"""
線上詢價模組

公開端（public_router）：官網訪客送出詢價，無需登入
  - 這是全系統唯一未登入即可寫入資料庫的入口，因此必須套用 rate limit，
    避免被灌爆或當成垃圾信管道。
後台端（router）：業務人員檢視、更新狀態、轉為正式客戶

【v2.0 新增】在此之前 `/quote` 頁面的送出按鈕只切換前端狀態、不呼叫任何 API，
使用者填寫的詢價資料會直接消失，業務端完全看不到。
"""
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, Tenant
from app.models.customer import Customer
from app.models.inquiry import Inquiry
from app.modules.inquiries.schemas import InquiryCreate, InquiryStatusUpdate, VALID_STATUSES
from app.rate_limit import limiter

router = APIRouter(prefix="/api/v1/inquiries", tags=["線上詢價"])
public_router = APIRouter(prefix="/api/v1/public/inquiries", tags=["官網公開API"])


def _serialize(i: Inquiry) -> dict:
    return {
        "id": str(i.id),
        "name": i.name,
        "company": i.company,
        "email": i.email,
        "phone": i.phone,
        "product_type": i.product_type,
        "quantity": i.quantity,
        "description": i.description,
        "status": i.status,
        "internal_notes": i.internal_notes,
        "converted_customer_id": str(i.converted_customer_id) if i.converted_customer_id else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


# ── 公開端（官網訪客，無需登入）────────────────────────────────

@public_router.post("", summary="送出線上詢價（官網公開）")
@limiter.limit("5/hour")
async def create_inquiry(
    request: Request,
    data: InquiryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    官網詢價表單送出。回應刻意不洩漏任何內部識別資訊以外的資料，
    也不回傳既有客戶是否存在，避免被當成客戶名單列舉工具。
    """
    # tenant_id 由後端決定，不接受前端傳入（防止跨租戶寫入）
    tenant_id = (await db.execute(select(Tenant.id).limit(1))).scalar_one_or_none()

    inquiry = Inquiry(
        tenant_id=tenant_id,
        name=data.name.strip(),
        company=(data.company or "").strip() or None,
        email=str(data.email).strip(),
        phone=(data.phone or "").strip() or None,
        product_type=data.product_type,
        quantity=data.quantity,
        description=data.description,
        source_page=data.source_page or "/quote",
    )
    db.add(inquiry)
    await db.flush()
    return {
        "success": True,
        "inquiry_id": str(inquiry.id),
        "message": "詢價已送出，業務人員將於1個工作日內與您聯繫",
    }


# ── 後台端（需登入）──────────────────────────────────────────

@router.get("", summary="詢價列表（後台）")
async def list_inquiries(
    status: Optional[str] = Query(None, description="new/contacted/quoted/won/lost/spam"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Inquiry).where(Inquiry.tenant_id == current_user.tenant_id)
    if status:
        q = q.where(Inquiry.status == status)
    q = q.order_by(Inquiry.created_at.desc())
    rows = (await db.execute(q)).scalars().all()

    # 順帶回傳各狀態筆數，前端不必為了顯示標籤再打一次 API
    count_q = (
        select(Inquiry.status, func.count(Inquiry.id))
        .where(Inquiry.tenant_id == current_user.tenant_id)
        .group_by(Inquiry.status)
    )
    counts = {s: c for s, c in (await db.execute(count_q)).all()}

    return {
        "success": True,
        "data": [_serialize(i) for i in rows],
        "total": len(rows),
        "status_counts": counts,
    }


@router.get("/{inquiry_id}", summary="詢價詳情（後台）")
async def get_inquiry(
    inquiry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Inquiry).where(Inquiry.id == inquiry_id, Inquiry.tenant_id == current_user.tenant_id)
    inquiry = (await db.execute(q)).scalar_one_or_none()
    if not inquiry:
        raise HTTPException(404, "找不到此詢價")
    return {"success": True, "data": _serialize(inquiry)}


@router.patch("/{inquiry_id}/status", summary="更新詢價處理狀態")
async def update_status(
    inquiry_id: UUID,
    data: InquiryStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.status not in VALID_STATUSES:
        raise HTTPException(400, f"狀態值不合法，僅接受：{'/'.join(sorted(VALID_STATUSES))}")

    q = select(Inquiry).where(Inquiry.id == inquiry_id, Inquiry.tenant_id == current_user.tenant_id)
    inquiry = (await db.execute(q)).scalar_one_or_none()
    if not inquiry:
        raise HTTPException(404, "找不到此詢價")

    inquiry.status = data.status
    if data.internal_notes is not None:
        inquiry.internal_notes = data.internal_notes
    inquiry.assigned_to = current_user.id
    await db.flush()
    return {"success": True, "message": f"詢價狀態已更新為 {data.status}"}


@router.post("/{inquiry_id}/convert-to-customer", summary="詢價轉為正式客戶")
async def convert_to_customer(
    inquiry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    把詢價資料帶入 customers 主檔，避免業務重複手key。
    已轉換過的詢價直接回傳既有客戶，不會重複建立（冪等）。
    """
    q = select(Inquiry).where(Inquiry.id == inquiry_id, Inquiry.tenant_id == current_user.tenant_id)
    inquiry = (await db.execute(q)).scalar_one_or_none()
    if not inquiry:
        raise HTTPException(404, "找不到此詢價")

    if inquiry.converted_customer_id:
        return {
            "success": True,
            "customer_id": str(inquiry.converted_customer_id),
            "message": "此詢價先前已轉為客戶，未重複建立",
            "already_converted": True,
        }

    # 產生客戶編號（沿用 customers 模組的 C0001 格式）
    count = (await db.execute(select(func.count(Customer.id)))).scalar() or 0
    code = f"C{count + 1:04d}"

    customer = Customer(
        tenant_id=current_user.tenant_id,
        code=code,
        name=inquiry.company or inquiry.name,
        contact_name=inquiry.name,
        contact_email=inquiry.email,
        contact_phone=inquiry.phone,
        notes=f"由官網詢價轉入（{inquiry.created_at:%Y-%m-%d}）\n需求：{inquiry.description or '—'}",
        created_by=current_user.id,
    )
    db.add(customer)
    await db.flush()

    inquiry.converted_customer_id = customer.id
    inquiry.status = "contacted"
    inquiry.updated_at = datetime.utcnow()
    await db.flush()

    return {
        "success": True,
        "customer_id": str(customer.id),
        "customer_code": code,
        "message": f"已建立客戶 {code} — {customer.name}",
        "already_converted": False,
    }
