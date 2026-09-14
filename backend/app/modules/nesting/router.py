from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.nesting import NestingJob, NestingPart
from app.modules.nesting.schemas import (
    NestingRequest, NestingResultOut, PresetCompareRequest, PresetCompareResponse,
)
from app.ai.nesting_bfd import BFDNestingEngine, Part as NestPart, compare_all_presets
from sqlalchemy import select
import uuid as uuid_mod

router = APIRouter(prefix="/api/v1/nesting", tags=["裁切最佳化"])

@router.post("/compare-presets", response_model=PresetCompareResponse, summary="比較9種板型，找出最省片數的方案")
async def compare_presets(
    data: PresetCompareRequest,
    current_user: User = Depends(get_current_user),
):
    nest_parts = [
        NestPart(
            id=p.label,
            label=p.label,
            length=float(p.length_mm),
            width=float(p.width_mm),
            quantity=p.quantity,
            can_rotate=p.can_rotate,
        )
        for p in data.parts
    ]
    result = compare_all_presets(nest_parts, kerf=float(data.kerf_mm))
    return result

@router.post("/calculate", summary="執行裁切最佳化計算")
async def calculate_nesting(
    data: NestingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 建立Job記錄
    job = NestingJob(
        tenant_id=current_user.tenant_id,
        wo_id=data.wo_id,
        material_id=data.material_id,
        sheet_length_mm=data.sheet_length_mm,
        sheet_width_mm=data.sheet_width_mm,
        kerf_mm=data.kerf_mm,
        status="running",
    )
    db.add(job)
    await db.flush()

    # 儲存零件清單
    for p in data.parts:
        part = NestingPart(
            nesting_job_id=job.id,
            bom_item_id=p.bom_item_id,
            label=p.label,
            part_length_mm=p.length_mm,
            part_width_mm=p.width_mm,
            quantity=p.quantity,
            can_rotate=p.can_rotate,
        )
        db.add(part)

    # 執行BFD演算法（同步，輕量任務直接執行）
    engine = BFDNestingEngine(
        sheet_length=float(data.sheet_length_mm),
        sheet_width=float(data.sheet_width_mm),
        kerf=float(data.kerf_mm),
    )
    nest_parts = [
        NestPart(
            id=p.label,
            label=p.label,
            length=float(p.length_mm),
            width=float(p.width_mm),
            quantity=p.quantity,
            can_rotate=p.can_rotate,
        )
        for p in data.parts
    ]
    result = engine.nest(nest_parts)

    # 儲存結果
    job.status = "completed"
    job.sheets_used = result["sheets_used"]
    job.utilization_rate = result["utilization_rate"]
    job.total_waste_area_mm2 = result["waste_area_mm2"]
    job.result_json = result

    await db.flush()

    return {
        "success": True,
        "job_id": str(job.id),
        "sheets_used": result["sheets_used"],
        "utilization_rate": f"{result['utilization_rate']*100:.1f}%",
        "waste_area_mm2": result["waste_area_mm2"],
        "placements": result["placements"],
        "remnants": result["remnants"],
    }

@router.get("/jobs/{job_id}", summary="查詢排版結果")
async def get_nesting_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(NestingJob).where(
        NestingJob.id == job_id,
        NestingJob.tenant_id == current_user.tenant_id,
    )
    result = await db.execute(q)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "找不到此排版任務")
    return {"success": True, "data": job.result_json, "job_id": str(job.id),
            "utilization_rate": float(job.utilization_rate) if job.utilization_rate else None,
            "sheets_used": job.sheets_used, "status": job.status}

@router.get("/jobs", summary="排版任務列表")
async def list_nesting_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(NestingJob).where(
        NestingJob.tenant_id == current_user.tenant_id
    ).order_by(NestingJob.created_at.desc()).limit(50)
    result = await db.execute(q)
    jobs = result.scalars().all()
    return {"success": True, "data": [
        {"id": str(j.id), "status": j.status, "sheets_used": j.sheets_used,
         "utilization_rate": float(j.utilization_rate) if j.utilization_rate else None,
         "created_at": j.created_at.isoformat()} for j in jobs
    ]}
