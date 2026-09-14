from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.modules.production.service import ProductionService, InsufficientStockError
from app.modules.production.schemas import (
    WorkOrderCreate, WorkOrderOut, OperationReportIn,
    MaterialIssueIn, WorkOrderCompleteIn,
)

router = APIRouter(prefix="/api/v1/work-orders", tags=["生產工單"])
svc = ProductionService()

@router.post("", summary="建立工單")
async def create_wo(
    data: WorkOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wo = await svc.create_work_order(db, current_user.tenant_id, current_user.id, data)
    return {"success": True, "wo_number": wo.wo_number, "wo_id": str(wo.id),
            "message": "工單建立成功，狀態為草稿，請確認後發佈"}

@router.get("", summary="工單列表")
async def list_wos(
    status: Optional[str] = Query(None, description="draft/released/in_progress/completed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wos = await svc.list_work_orders(db, current_user.tenant_id, status)
    return {"success": True, "data": [
        {"id": str(w.id), "wo_number": w.wo_number, "quantity": w.quantity,
         "status": w.status, "priority": w.priority,
         "planned_start": w.planned_start.isoformat() if w.planned_start else None,
         "planned_end": w.planned_end.isoformat() if w.planned_end else None}
        for w in wos
    ], "total": len(wos)}

@router.get("/{wo_id}", summary="工單詳情（含工序清單，供MES使用）")
async def get_wo_detail(
    wo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wo = await svc.get_work_order_detail(db, wo_id, current_user.tenant_id)
    if not wo:
        raise HTTPException(404, "找不到此工單")
    return {"success": True, "data": {
        "id": str(wo.id), "wo_number": wo.wo_number, "quantity": wo.quantity,
        "status": wo.status, "priority": wo.priority,
        "planned_start": wo.planned_start.isoformat() if wo.planned_start else None,
        "planned_end": wo.planned_end.isoformat() if wo.planned_end else None,
        "operations": [
            {
                "id": str(op.id), "op_seq": op.op_seq, "op_name": op.op_name,
                "status": op.status, "good_qty": op.good_qty, "scrap_qty": op.scrap_qty,
                "actual_start": op.actual_start.isoformat() if op.actual_start else None,
                "actual_end": op.actual_end.isoformat() if op.actual_end else None,
            }
            for op in sorted(wo.operations, key=lambda o: o.op_seq)
        ],
    }}

@router.post("/{wo_id}/release", summary="發佈工單（草稿→已發佈）")
async def release(
    wo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wo = await svc.release_work_order(db, wo_id, current_user.tenant_id)
    if not wo:
        raise HTTPException(404, "找不到工單或狀態不是草稿")
    return {"success": True, "message": f"工單 {wo.wo_number} 已發佈"}

@router.post("/{wo_id}/operations/{op_id}/start", summary="MES報工：開始工序")
async def start_op(
    wo_id: UUID,
    op_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    op = await svc.start_operation(db, wo_id, op_id, current_user.id)
    if not op:
        raise HTTPException(404, "找不到此工序")
    return {"success": True, "message": f"工序【{op.op_name}】已開始", "started_at": op.actual_start}

@router.post("/{wo_id}/operations/{op_id}/complete", summary="MES報工：完成工序")
async def complete_op(
    wo_id: UUID,
    op_id: UUID,
    data: OperationReportIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    op = await svc.complete_operation(db, wo_id, op_id, data.good_qty, data.scrap_qty)
    if not op:
        raise HTTPException(404, "找不到此工序")
    yield_rate = data.good_qty / (data.good_qty + data.scrap_qty) * 100 if (data.good_qty + data.scrap_qty) > 0 else 0
    return {"success": True, "message": f"工序【{op.op_name}】完成",
            "good_qty": data.good_qty, "scrap_qty": data.scrap_qty,
            "yield_rate": f"{yield_rate:.1f}%"}

@router.get("/{wo_id}/material-plan", summary="工單備料清單")
async def material_plan(
    wo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await svc.get_material_plan(db, wo_id)
    return {"success": True, "wo_id": str(wo_id), "data": [
        {"material_id": str(i.material_id), "planned_qty": float(i.planned_qty),
         "issued_qty": float(i.issued_qty),
         "remaining": float(i.planned_qty - i.issued_qty)}
        for i in items
    ]}


@router.post("/{wo_id}/issue-materials", summary="工單發料（自動扣減原料庫存）")
async def issue_materials(
    wo_id: UUID,
    data: MaterialIssueIn = MaterialIssueIn(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    依備料清單一次性發料並扣減庫存。任一項庫存不足即整批拒絕（回 409），
    回應中的 shortages 列出每項缺多少，倉管可據此開採購單。
    """
    try:
        result = await svc.issue_materials(
            db, wo_id, current_user.tenant_id, current_user.id, data.warehouse_code
        )
    except InsufficientStockError as e:
        raise HTTPException(409, detail={"message": "庫存不足，未發出任何料件", "shortages": e.shortages})
    except ValueError as e:
        raise HTTPException(400, str(e))
    if result is None:
        raise HTTPException(404, "找不到此工單")
    return {
        "success": True,
        "message": f"工單 {result['wo_number']} 發料完成，共 {len(result['issued'])} 項料件已扣庫存"
        if result["issued"] else f"工單 {result['wo_number']} 備料清單已全數發料，本次無需再發",
        "data": result["issued"],
    }


@router.post("/{wo_id}/complete", summary="工單完工入庫（成品進FG倉）")
async def complete_work_order(
    wo_id: UUID,
    data: WorkOrderCompleteIn = WorkOrderCompleteIn(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全部工序完成後，將良品數入FG倉並把工單狀態轉為 completed。"""
    try:
        result = await svc.complete_work_order(
            db, wo_id, current_user.tenant_id, current_user.id,
            data.good_qty, data.warehouse_code,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    if result is None:
        raise HTTPException(404, "找不到此工單")
    return {
        "success": True,
        "message": f"工單 {result['wo_number']} 完工入庫 {result['received_qty']} 件（計畫 {result['planned_qty']} 件）",
        "data": result,
    }
