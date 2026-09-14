"""
官網作品展示系統 — 公開端點（無需登入），供官網前端讀取案例資料
管理端點需登入，供後台維護案例內容
"""
import json
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.portfolio import PortfolioCase

router = APIRouter(prefix="/api/v1/portfolio", tags=["作品展示系統"])
public_router = APIRouter(prefix="/api/v1/public/portfolio", tags=["官網公開API"])

class PortfolioCreate(BaseModel):
    title: str
    client_name: Optional[str] = None
    industry: Optional[str] = None
    product_type: Optional[str] = None
    dimensions: Optional[str] = None
    materials: Optional[str] = None
    cover_image_url: Optional[str] = None
    gallery_urls: list[str] = []
    challenge: Optional[str] = None
    solution: Optional[str] = None
    result: Optional[str] = None
    is_featured: bool = False

def _slugify(title: str) -> str:
    import re
    import time
    base = re.sub(r"[^\w\u4e00-\u9fff-]", "-", title.lower())
    return f"{base}-{int(time.time())}"[:200]

# ── 管理端（需登入）
@router.post("", summary="新增作品案例")
async def create_case(
    data: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = PortfolioCase(
        tenant_id=current_user.tenant_id,
        title=data.title,
        client_name=data.client_name,
        industry=data.industry,
        product_type=data.product_type,
        dimensions=data.dimensions,
        materials=data.materials,
        cover_image_url=data.cover_image_url,
        gallery_urls_json=json.dumps(data.gallery_urls),
        slug=_slugify(data.title),
        challenge=data.challenge,
        solution=data.solution,
        result=data.result,
        is_featured=data.is_featured,
    )
    db.add(case)
    await db.flush()
    return {"success": True, "case_id": str(case.id), "slug": case.slug}

@router.get("", summary="作品案例列表（後台管理）")
async def list_cases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(PortfolioCase).where(
        PortfolioCase.tenant_id == current_user.tenant_id
    ).order_by(PortfolioCase.sort_order, PortfolioCase.created_at.desc())
    result = await db.execute(q)
    cases = result.scalars().all()
    return {"success": True, "data": [
        {"id": str(c.id), "title": c.title, "industry": c.industry,
         "is_featured": c.is_featured, "slug": c.slug,
         "published": c.published_at is not None}
        for c in cases
    ]}

@router.post("/{case_id}/publish", summary="發佈作品到官網")
async def publish_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime
    q = select(PortfolioCase).where(PortfolioCase.id == case_id,
                                     PortfolioCase.tenant_id == current_user.tenant_id)
    result = await db.execute(q)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "找不到此作品案例")
    case.published_at = datetime.utcnow()
    return {"success": True, "message": f"作品「{case.title}」已發佈至官網"}

# ── 公開端（官網讀取，無需登入）
@public_router.get("", summary="官網作品列表（公開）")
async def public_list_cases(
    industry: Optional[str] = Query(None),
    featured_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    q = select(PortfolioCase).where(PortfolioCase.published_at.isnot(None))
    if industry:
        q = q.where(PortfolioCase.industry == industry)
    if featured_only:
        q = q.where(PortfolioCase.is_featured == True)
    q = q.order_by(PortfolioCase.sort_order)
    result = await db.execute(q)
    cases = result.scalars().all()
    return {"success": True, "data": [
        {"title": c.title, "slug": c.slug, "industry": c.industry,
         "product_type": c.product_type, "cover_image_url": c.cover_image_url,
         "dimensions": c.dimensions}
        for c in cases
    ]}

@public_router.get("/{slug}", summary="官網作品詳情（公開）")
async def public_get_case(slug: str, db: AsyncSession = Depends(get_db)):
    q = select(PortfolioCase).where(PortfolioCase.slug == slug,
                                     PortfolioCase.published_at.isnot(None))
    result = await db.execute(q)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "找不到此作品案例")
    return {"success": True, "data": {
        "title": case.title, "client_name": case.client_name,
        "industry": case.industry, "product_type": case.product_type,
        "dimensions": case.dimensions, "materials": case.materials,
        "cover_image_url": case.cover_image_url,
        "gallery_urls": json.loads(case.gallery_urls_json) if case.gallery_urls_json else [],
        "challenge": case.challenge, "solution": case.solution, "result": case.result,
    }}
