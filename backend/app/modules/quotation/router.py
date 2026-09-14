from uuid import UUID
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.quotation import Quotation, QuotationItem
from app.models.customer import Customer
from app.modules.quotation.schemas import QuotationCreate, AIEstimateRequest, QuotationOut
from app.ai.quote_engine import QuoteEngine
from app.modules.quotation.pdf_export import generate_quotation_pdf
import uuid as uuid_mod

router = APIRouter(prefix="/api/v1/quotations", tags=["報價管理"])

async def _next_quote_number(db: AsyncSession) -> str:
    year = date.today().year
    q = select(func.count(Quotation.id)).where(
        Quotation.quote_number.like(f"Q{year}-%")
    )
    count = (await db.execute(q)).scalar() or 0
    return f"Q{year}-{count+1:04d}"

@router.post("/ai-estimate", summary="AI快速估價（無需建立客戶）")
async def ai_estimate(
    data: AIEstimateRequest,
    current_user: User = Depends(get_current_user),
):
    engine = QuoteEngine(target_margin=data.target_margin or 0.35)
    result = engine.generate_quote(data.acrylic_items, data.operations, data.quantity)
    return {"success": True, "estimate": result,
            "note": "此為AI估算值，正式報價請由業務確認後建立報價單"}

@router.post("", summary="建立報價單")
async def create_quotation(
    data: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote_number = await _next_quote_number(db)
    engine = QuoteEngine(target_margin=float(data.profit_margin))

    total_material = 0.0
    total_processing = 0.0
    total_amount = 0.0  # 修正bug#12：所有品項小計加總，無論手動定價或AI試算都會計入
    items_out = []

    for i, item in enumerate(data.items, 1):
        # 計算此明細的成本
        acrylic_cost = 0.0
        proc_cost = 0.0
        if item.unit_price is None:
            # 用BOM資訊自動計算
            acrylic_cost = float(item.acrylic_cai or 0) * 145  # 預設3mm透明價
            cnc = float(item.cnc_minutes or 0) * 8
            laser = float(item.laser_meters or 0) * 120  # 雷射每米成本
            assembly = float(item.assembly_hours or 0) * 240
            proc_cost = cnc + laser + assembly
            subtotal = (acrylic_cost + proc_cost) * 1.25  # 25%管銷
            unit_price = subtotal / (1 - float(data.profit_margin))
        else:
            unit_price = float(item.unit_price)

        total_material += acrylic_cost * item.quantity
        total_processing += proc_cost * item.quantity
        total_amount += unit_price * item.quantity
        items_out.append({**item.model_dump(), "line_no": i, "unit_price": unit_price})

    overhead = (total_material + total_processing) * 0.25
    # 修正bug#12：final_price 改用「所有品項小計加總」，
    # 舊寫法只用 material/processing 成本反推，手動定價品項的unit_price不會反映到header總額，
    # 導致PDF匯出時品項顯示888元、但報價單總額顯示0元的資料不一致問題。
    final_price = total_amount

    q = Quotation(
        tenant_id=current_user.tenant_id,
        quote_number=quote_number,
        customer_id=data.customer_id,
        valid_until=data.valid_until or (date.today() + timedelta(days=30)),
        material_cost=total_material,
        processing_cost=total_processing,
        overhead_cost=overhead,
        profit_margin=data.profit_margin,
        final_price=final_price,
        notes=data.notes,
        ai_generated=True,
        created_by=current_user.id,
    )
    db.add(q)
    await db.flush()

    for i, item in enumerate(data.items, 1):
        qi = QuotationItem(
            quotation_id=q.id,
            line_no=i,
            product_id=item.product_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=items_out[i-1]["unit_price"],
            acrylic_cai=item.acrylic_cai,
            cnc_minutes=item.cnc_minutes,
            laser_meters=item.laser_meters,
            assembly_hours=item.assembly_hours,
        )
        db.add(qi)

    return {"success": True, "quote_number": quote_number,
            "final_price": round(final_price, 0), "quotation_id": str(q.id)}

@router.get("", summary="報價單列表")
async def list_quotations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Quotation).where(
        Quotation.tenant_id == current_user.tenant_id
    ).order_by(Quotation.created_at.desc()).limit(100)
    result = await db.execute(q)
    quotes = result.scalars().all()
    return {"success": True, "data": [
        {"id": str(q.id), "quote_number": q.quote_number, "status": q.status,
         "final_price": float(q.final_price), "created_at": q.created_at.isoformat()}
        for q in quotes
    ]}

@router.patch("/{quote_id}/status", summary="更新報價狀態")
async def update_status(
    quote_id: UUID,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed = {"sent", "accepted", "rejected", "expired"}
    if status not in allowed:
        raise HTTPException(400, f"狀態必須是: {allowed}")
    q = select(Quotation).where(Quotation.id == quote_id, Quotation.tenant_id == current_user.tenant_id)
    result = await db.execute(q)
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, "找不到此報價單")
    quote.status = status
    return {"success": True, "message": f"報價單狀態更新為 {status}"}

@router.get("/{quote_id}/pdf", summary="匯出報價單PDF")
async def export_pdf(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Quotation).where(Quotation.id == quote_id, Quotation.tenant_id == current_user.tenant_id)
    result = await db.execute(q)
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, "找不到此報價單")

    cust_q = select(Customer).where(Customer.id == quote.customer_id)
    customer = (await db.execute(cust_q)).scalar_one_or_none()

    items_q = select(QuotationItem).where(QuotationItem.quotation_id == quote_id).order_by(QuotationItem.line_no)
    items = (await db.execute(items_q)).scalars().all()

    pdf_bytes = generate_quotation_pdf(
        quotation={
            "quote_number": quote.quote_number,
            "status": quote.status,
            "valid_until": quote.valid_until,
            "final_price": quote.final_price,
            "material_cost": quote.material_cost,
            "processing_cost": quote.processing_cost,
            "overhead_cost": quote.overhead_cost,
            "notes": quote.notes,
            "created_at": quote.created_at,
        },
        customer={
            "name": customer.name if customer else "—",
            "contact_name": customer.contact_name if customer else "—",
            "contact_phone": customer.contact_phone if customer else "—",
        },
        items=[{
            "line_no": i.line_no,
            "description": i.description,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
        } for i in items],
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.quote_number}.pdf"'},
    )
