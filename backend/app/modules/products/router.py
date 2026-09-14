from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.product import Product, BomHeader, BomItem
from app.models.material import Material
from app.modules.products.schemas import (
    ProductCreate, ProductOut, BomCreate, BomOut, MaterialCreate, MaterialOut
)

router = APIRouter(prefix="/api/v1", tags=["產品與BOM"])

# ── Materials ────────────────────────────────────────────────────────
@router.get("/materials", summary="物料主檔列表")
async def list_materials(
    material_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Material).where(Material.tenant_id == current_user.tenant_id, Material.is_active == True)
    if material_type:
        q = q.where(Material.material_type == material_type)
    if search:
        q = q.where(Material.name.ilike(f"%{search}%"))
    mats = (await db.execute(q)).scalars().all()
    return {"success": True, "data": mats}

@router.post("/materials", summary="新增物料")
async def create_material(
    data: MaterialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mat = Material(tenant_id=current_user.tenant_id, **data.model_dump())
    db.add(mat)
    await db.flush()
    return {"success": True, "material_id": str(mat.id)}

# ── Products ─────────────────────────────────────────────────────────
@router.get("/products", summary="產品列表")
async def list_products(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Product).where(Product.tenant_id == current_user.tenant_id, Product.is_active == True)
    if category:
        q = q.where(Product.category == category)
    prods = (await db.execute(q)).scalars().all()
    return {"success": True, "data": prods}

@router.post("/products", summary="新增產品")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = Product(tenant_id=current_user.tenant_id, **data.model_dump())
    db.add(p)
    await db.flush()
    return {"success": True, "product_id": str(p.id)}

# ── BOM ──────────────────────────────────────────────────────────────
@router.get("/products/{product_id}/bom", summary="取得產品BOM")
async def get_bom(
    product_id: UUID,
    version: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(BomHeader).where(BomHeader.product_id == product_id)
    if version:
        q = q.where(BomHeader.version == version)
    else:
        q = q.where(BomHeader.status == "active")
    bom = (await db.execute(q)).scalar_one_or_none()
    if not bom:
        raise HTTPException(404, "找不到BOM，請先建立")
    return {"success": True, "data": bom}

@router.post("/bom", summary="建立BOM")
async def create_bom(
    data: BomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bom = BomHeader(
        product_id=data.product_id,
        version=data.version,
        effective_date=data.effective_date,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(bom)
    await db.flush()
    for item in data.items:
        bi = BomItem(bom_id=bom.id, **item.model_dump())
        db.add(bi)
    return {"success": True, "bom_id": str(bom.id)}

@router.post("/bom/{bom_id}/approve", summary="審核發佈BOM")
async def approve_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(BomHeader).where(BomHeader.id == bom_id)
    bom = (await db.execute(q)).scalar_one_or_none()
    if not bom:
        raise HTTPException(404, "找不到BOM")
    # 將同產品的舊版本設為obsolete
    old_q = select(BomHeader).where(
        BomHeader.product_id == bom.product_id,
        BomHeader.status == "active",
        BomHeader.id != bom_id,
    )
    for old in (await db.execute(old_q)).scalars().all():
        old.status = "obsolete"
    bom.status = "active"
    bom.approved_by = current_user.id
    return {"success": True, "message": f"BOM v{bom.version} 已發佈"}

@router.get("/bom/{bom_id}/expand", summary="BOM完整展開（含子件）")
async def expand_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(BomHeader).where(BomHeader.id == bom_id)
    bom = (await db.execute(q)).scalar_one_or_none()
    if not bom:
        raise HTTPException(404, "找不到BOM")
    # 展開BOM（取得每個item的material詳情）
    items_q = select(BomItem, Material).join(Material, BomItem.material_id == Material.id).where(BomItem.bom_id == bom_id)
    rows = (await db.execute(items_q)).all()
    expanded = []
    for bi, mat in rows:
        qty_with_waste = float(bi.quantity) * (1 + float(bi.wastage_rate))
        expanded.append({
            "line_no": bi.line_no,
            "material_id": str(mat.id),
            "material_name": mat.name,
            "material_type": mat.material_type,
            "thickness_mm": float(mat.thickness_mm) if mat.thickness_mm else None,
            "color": mat.color,
            "cut_length_mm": float(bi.cut_length_mm) if bi.cut_length_mm else None,
            "cut_width_mm": float(bi.cut_width_mm) if bi.cut_width_mm else None,
            "quantity": float(bi.quantity),
            "wastage_rate": float(bi.wastage_rate),
            "quantity_with_waste": round(qty_with_waste, 4),
            "unit": bi.unit,
            "unit_cost": float(mat.unit_cost),
            "line_cost": round(qty_with_waste * float(mat.unit_cost), 2),
        })
    return {"success": True, "bom_id": str(bom_id), "items": expanded,
            "total_material_cost": round(sum(i["line_cost"] for i in expanded), 2)}
