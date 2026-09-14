from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.production import WorkOrder
from app.models.nesting import NestingJob
from app.models.inventory import InventoryBalance, InventoryTransaction
from app.models.quotation import Quotation
from app.models.equipment import Equipment, MaintenanceLog

router = APIRouter(prefix="/api/v1/analytics", tags=["分析報表"])

@router.get("/dashboard", summary="廠長儀表板")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = current_user.tenant_id
    today = date.today()
    month_start = today.replace(day=1)

    # 本月工單數
    wo_q = select(func.count(WorkOrder.id)).where(
        WorkOrder.tenant_id == tid,
        WorkOrder.created_at >= month_start,
    )
    wo_count = (await db.execute(wo_q)).scalar() or 0

    # 進行中工單
    active_q = select(func.count(WorkOrder.id)).where(
        WorkOrder.tenant_id == tid,
        WorkOrder.status.in_(["released", "in_progress"]),
    )
    active_count = (await db.execute(active_q)).scalar() or 0

    # 本月平均板材利用率
    nesting_q = select(func.avg(NestingJob.utilization_rate)).where(
        NestingJob.tenant_id == tid,
        NestingJob.created_at >= month_start,
        NestingJob.status == "completed",
    )
    avg_util = (await db.execute(nesting_q)).scalar()
    avg_util_pct = float(avg_util) * 100 if avg_util else 0

    # 本月工單準時率（planned_end >= actual_end 或尚未完工）
    completed_q = select(func.count(WorkOrder.id)).where(
        WorkOrder.tenant_id == tid,
        WorkOrder.status == "completed",
        WorkOrder.created_at >= month_start,
    )
    completed = (await db.execute(completed_q)).scalar() or 0

    on_time_q = select(func.count(WorkOrder.id)).where(
        WorkOrder.tenant_id == tid,
        WorkOrder.status == "completed",
        WorkOrder.created_at >= month_start,
        WorkOrder.actual_end <= func.cast(WorkOrder.planned_end, WorkOrder.actual_end.type),
    )
    on_time = (await db.execute(on_time_q)).scalar() or 0
    on_time_rate = (on_time / completed * 100) if completed > 0 else 0

    # 本月報價數與成交率
    quote_q = select(func.count(Quotation.id)).where(
        Quotation.tenant_id == tid,
        Quotation.created_at >= month_start,
    )
    quote_count = (await db.execute(quote_q)).scalar() or 0

    won_q = select(func.count(Quotation.id)).where(
        Quotation.tenant_id == tid,
        Quotation.status == "accepted",
        Quotation.created_at >= month_start,
    )
    won_count = (await db.execute(won_q)).scalar() or 0

    return {
        "success": True,
        "period": {"month": today.strftime("%Y年%m月"), "as_of": today.isoformat()},
        "kpi": {
            "monthly_work_orders": wo_count,
            "active_work_orders": active_count,
            "avg_material_utilization_pct": round(avg_util_pct, 1),
            "on_time_delivery_rate_pct": round(on_time_rate, 1),
            "monthly_quotes": quote_count,
            "quote_win_rate_pct": round(won_count / quote_count * 100, 1) if quote_count > 0 else 0,
        }
    }

@router.get("/material-utilization", summary="板材利用率月報")
async def material_utilization(
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = date.today() - timedelta(days=months * 30)
    q = select(
        func.date_trunc("month", NestingJob.created_at).label("month"),
        func.avg(NestingJob.utilization_rate).label("avg_util"),
        func.count(NestingJob.id).label("job_count"),
        func.sum(NestingJob.sheets_used).label("total_sheets"),
    ).where(
        NestingJob.tenant_id == current_user.tenant_id,
        NestingJob.status == "completed",
        NestingJob.created_at >= since,
    ).group_by("month").order_by("month")

    result = await db.execute(q)
    rows = result.all()
    return {"success": True, "data": [
        {
            "month": row.month.strftime("%Y-%m") if row.month else None,
            "avg_utilization_pct": round(float(row.avg_util) * 100, 1) if row.avg_util else 0,
            "nesting_jobs": row.job_count,
            "total_sheets_used": row.total_sheets or 0,
        }
        for row in rows
    ]}

@router.get("/cost-breakdown", summary="成本分解分析")
async def cost_breakdown(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    month_start = date.today().replace(day=1)
    q = select(
        func.sum(Quotation.material_cost).label("total_material"),
        func.sum(Quotation.processing_cost).label("total_processing"),
        func.sum(Quotation.overhead_cost).label("total_overhead"),
        func.sum(Quotation.final_price).label("total_revenue"),
        func.avg(Quotation.profit_margin).label("avg_margin"),
    ).where(
        Quotation.tenant_id == current_user.tenant_id,
        Quotation.status == "accepted",
        Quotation.created_at >= month_start,
    )
    result = await db.execute(q)
    row = result.one()

    total_cost = float(row.total_material or 0) + float(row.total_processing or 0) + float(row.total_overhead or 0)
    revenue = float(row.total_revenue or 0)

    return {"success": True, "data": {
        "material_cost": float(row.total_material or 0),
        "processing_cost": float(row.total_processing or 0),
        "overhead_cost": float(row.total_overhead or 0),
        "total_cost": total_cost,
        "total_revenue": revenue,
        "gross_profit": revenue - total_cost,
        "avg_margin_pct": round(float(row.avg_margin or 0) * 100, 1),
        "cost_breakdown_pct": {
            "material": round(float(row.total_material or 0) / total_cost * 100, 1) if total_cost > 0 else 0,
            "processing": round(float(row.total_processing or 0) / total_cost * 100, 1) if total_cost > 0 else 0,
            "overhead": round(float(row.total_overhead or 0) / total_cost * 100, 1) if total_cost > 0 else 0,
        }
    }}

@router.get("/equipment-oee", summary="設備稼動率（OEE）")
async def equipment_oee(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Equipment).where(
        Equipment.tenant_id == current_user.tenant_id,
        Equipment.status != "retired",
    )
    result = await db.execute(q)
    eqs = result.scalars().all()

    month_start = date.today().replace(day=1)
    oee_data = []
    for eq in eqs:
        # 計算本月停機時數（從maintenance logs）
        maint_q = select(func.sum(MaintenanceLog.downtime_hours)).where(
            MaintenanceLog.equipment_id == eq.id,
            MaintenanceLog.performed_at >= month_start,
        )
        downtime = (await db.execute(maint_q)).scalar() or 0
        working_days = date.today().day
        available_hours = working_days * 8  # 每日8小時
        uptime_rate = max(0, (available_hours - float(downtime)) / available_hours * 100) if available_hours > 0 else 0

        oee_data.append({
            "equipment_id": str(eq.id),
            "code": eq.code,
            "name": eq.name,
            "type": eq.equipment_type,
            "status": eq.status,
            "downtime_hours_mtd": float(downtime),
            "availability_pct": round(uptime_rate, 1),
        })

    return {"success": True, "data": oee_data}
