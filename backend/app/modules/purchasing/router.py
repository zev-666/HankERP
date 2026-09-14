from uuid import UUID
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.purchasing import PurchaseOrder, PoItem
from app.modules.purchasing.schemas import PurchaseOrderCreate, ReceiveItemIn
from app.modules.inventory.service import InventoryService
from app.modules.inventory.schemas import TransactionCreate, SheetStockCreate

router = APIRouter(prefix="/api/v1/purchase-orders", tags=["採購管理"])
inv_svc = InventoryService()

async def _next_po_number(db: AsyncSession) -> str:
    year = date.today().year
    q = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.po_number.like(f"PO{year}-%"))
    count = (await db.execute(q)).scalar() or 0
    return f"PO{year}-{count+1:04d}"

@router.post("", summary="建立採購單")
async def create_po(
    data: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po_number = await _next_po_number(db)
    total = sum(i.ordered_qty * i.unit_price for i in data.items)

    po = PurchaseOrder(
        tenant_id=current_user.tenant_id,
        po_number=po_number,
        supplier_id=data.supplier_id,
        expected_date=data.expected_date,
        total_amount=total,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(po)
    await db.flush()

    for i, item in enumerate(data.items, 1):
        pi = PoItem(
            po_id=po.id,
            line_no=i,
            material_id=item.material_id,
            ordered_qty=item.ordered_qty,
            unit_price=item.unit_price,
            unit=item.unit,
            sheet_thickness_mm=item.sheet_thickness_mm,
            sheet_length_mm=item.sheet_length_mm,
            sheet_width_mm=item.sheet_width_mm,
            sheet_color=item.sheet_color,
            notes=item.notes,
        )
        db.add(pi)

    return {"success": True, "po_number": po_number, "po_id": str(po.id),
            "total_amount": float(total)}

@router.get("", summary="採購單列表")
async def list_pos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(PurchaseOrder).where(
        PurchaseOrder.tenant_id == current_user.tenant_id
    ).order_by(PurchaseOrder.created_at.desc()).limit(100)
    result = await db.execute(q)
    pos = result.scalars().all()
    return {"success": True, "data": [
        {"id": str(p.id), "po_number": p.po_number, "status": p.status,
         "total_amount": float(p.total_amount),
         "expected_date": p.expected_date.isoformat() if p.expected_date else None}
        for p in pos
    ]}

@router.post("/{po_id}/confirm", summary="確認採購單（發給供應商）")
async def confirm_po(
    po_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(PurchaseOrder).where(PurchaseOrder.id == po_id,
                                     PurchaseOrder.tenant_id == current_user.tenant_id)
    result = await db.execute(q)
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, "找不到採購單")
    if po.status != "draft":
        raise HTTPException(400, "只有草稿狀態才能確認")
    po.status = "sent"
    return {"success": True, "message": f"採購單 {po.po_number} 已確認發送給供應商"}

@router.post("/{po_id}/receive", summary="進貨驗收（同步入庫）")
async def receive_goods(
    po_id: UUID,
    items: list[ReceiveItemIn],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(PurchaseOrder).where(PurchaseOrder.id == po_id,
                                     PurchaseOrder.tenant_id == current_user.tenant_id)
    result = await db.execute(q)
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, "找不到採購單")

    received_items = []
    for recv in items:
        # 更新PO明細收量
        pi_q = select(PoItem).where(PoItem.id == recv.po_item_id, PoItem.po_id == po_id)
        pi_res = await db.execute(pi_q)
        pi = pi_res.scalar_one_or_none()
        if pi:
            pi.received_qty += recv.received_qty

            # 若是壓克力板材，建立SheetStock記錄
            if recv.actual_length_mm:
                sheet_data = SheetStockCreate(
                    material_id=pi.material_id,
                    batch_no=recv.batch_no or po.po_number,
                    actual_length_mm=recv.actual_length_mm or pi.sheet_length_mm,
                    actual_width_mm=recv.actual_width_mm or pi.sheet_width_mm,
                    quantity=int(recv.received_qty),
                )
                await inv_svc.receive_sheets(db, current_user.tenant_id, current_user.id, sheet_data)
            else:
                # 一般物料入庫
                txn = TransactionCreate(
                    material_id=pi.material_id,
                    warehouse_code="RAW",
                    qty=recv.received_qty,
                    unit_cost=pi.unit_price,
                    source_type="PO",
                    source_id=po_id,
                    lot_number=recv.batch_no,
                    notes=recv.quality_notes,
                )
                await inv_svc.create_transaction(db, current_user.tenant_id,
                                                  current_user.id, txn, "RECEIPT")
            received_items.append(str(pi.material_id))

    po.status = "received"
    return {"success": True, "message": f"進貨驗收完成，已入庫 {len(received_items)} 項物料"}
