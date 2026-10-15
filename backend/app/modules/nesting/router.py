from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_commit_route import CommitBeforeResponseRoute
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.nesting import NestingJob, NestingPart
from app.modules.nesting.schemas import (
    NestingRequest, PresetCompareRequest, PresetCompareResponse,
)
from app.modules.nesting.service import ENGINE_VERSION, compare_presets, run_nesting
from sqlalchemy import select

router = APIRouter(route_class=CommitBeforeResponseRoute, prefix="/api/v1/nesting", tags=["裁切最佳化"])

@router.post("/compare-presets", response_model=PresetCompareResponse, summary="比較9種板型，找出最省片數的方案")
async def compare_presets_endpoint(
    data: PresetCompareRequest,
    current_user: User = Depends(get_current_user),
):
    return compare_presets(
        data.parts, data.kerf_mm, data.trim_mm, data.rem_pref, data.min_remnant_mm,
    )

@router.post("/calculate", summary="執行裁切最佳化計算（開條引擎，含刀序）")
async def calculate_nesting(
    data: NestingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    v2.3：排版核心由 Guillotine BFD 換成開條引擎（`app/ai/nesting_strip.py`）。

    舊引擎的排版品質明顯不足——同一組輸入 460×160×100 要 9 張板（利用率 32.5%），
    開條引擎只要 4 張（73.1%）。新引擎另外產出條帶結構與完整刀序（Level 3），
    這是現場真正要拿去裁板機用的東西。

    `result_json.engine` 記錄演算法版本；舊紀錄沒有這個鍵就是 v2.2 以前的 BFD 結果。
    """
    result = run_nesting(
        data.parts, data.sheet_length_mm, data.sheet_width_mm, data.kerf_mm,
        data.trim_mm, data.rem_pref, data.min_remnant_mm, data.max_sheets,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])

    job = NestingJob(
        tenant_id=current_user.tenant_id,
        wo_id=data.wo_id,
        material_id=data.material_id,
        sheet_length_mm=data.sheet_length_mm,
        sheet_width_mm=data.sheet_width_mm,
        kerf_mm=data.kerf_mm,
        algorithm_version=ENGINE_VERSION,
        status="running",
    )
    db.add(job)
    await db.flush()

    for p in data.parts:
        db.add(NestingPart(
            nesting_job_id=job.id,
            bom_item_id=p.bom_item_id,
            label=p.label,
            part_length_mm=p.length_mm,
            part_width_mm=p.width_mm,
            quantity=p.quantity,
            can_rotate=p.can_rotate,
        ))

    # 有零件排不進去時標 partial，不進 KPI（v2.1 起的規則，v2.3 維持）
    unplaced = result["unplaced"]
    job.status = "partial" if unplaced else "completed"
    job.sheets_used = result["sheets_used"]
    job.utilization_rate = result["utilization_rate"]
    job.total_waste_area_mm2 = result["waste_area_mm2"]
    job.result_json = result

    await db.flush()

    if unplaced:
        message = (f"有 {len(unplaced)} 件零件排不進 "
                   f"{data.sheet_length_mm}×{data.sheet_width_mm} 原板，"
                   f"請檢查尺寸或改用較大板型")
    else:
        message = (f"全部 {result['requested_count']} 件已排入，"
                   f"共 {result['sheets_used']} 張板、{result['total_cuts']} 刀")

    return {
        "success": True,
        "message": message,
        "job_id": str(job.id),
        "status": job.status,
        "utilization_rate_pct": f"{result['utilization_rate'] * 100:.1f}%",
        **result,
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
