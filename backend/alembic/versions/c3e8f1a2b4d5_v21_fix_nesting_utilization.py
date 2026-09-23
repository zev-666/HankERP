"""v2.1: 修正 nesting_jobs 歷史利用率（資料修正，不改 schema）

Revision ID: c3e8f1a2b4d5
Revises: b2d7a1c94e30
Create Date: 2026-09-23

為什麼：
  舊版 BFDNestingEngine 的利用率分子用「需求零件總面積」，不是「實際放上板的面積」。
  零件排不下時會回報 100%，這個數字寫進 nesting_jobs.utilization_rate，
  再被 analytics 的 avg() 拿去算廠長儀表板 KPI 與板材利用率月報。
  使用者 2026-09-19 同意修正可以改變歷史數字。

做法：
  由每筆 job 的 result_json.placements 重算
    utilization_rate      = Σ(placed_length × placed_width) ÷ (sheets_used × 板長 × 板寬)
    total_waste_area_mm2  = sheets_used × 板面積 − 放置面積
  一件都沒排進去 → sheets_used = 0、利用率 0。
  排入件數 < nesting_parts 需求件數 → status 改為 'partial'（analytics 只統計 'completed'）。
  舊值備份在 result_json.legacy_v20（utilization_rate / waste_area_mm2 / sheets_used / status），
  downgrade 由此還原。

安全性：
  只動 result_json 有 placements 的列；沒有 placements 的列（pending / failed / 舊格式）不碰。
  已經有 legacy_v20 的列跳過，重跑不會重複覆蓋備份。
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3e8f1a2b4d5"
down_revision: Union[str, None] = "b2d7a1c94e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def recompute(result_json: dict, sheet_length: float, sheet_width: float,
              requested_count: int, status: str) -> dict:
    """純函式：給一筆舊 job，回傳修正後的欄位。沒有 placements 回傳 None。"""
    placements = result_json.get("placements")
    if not isinstance(placements, list):
        return None
    placed_area = sum(float(p["placed_length"]) * float(p["placed_width"]) for p in placements)
    sheets_used = (max(int(p["sheet_index"]) for p in placements) + 1) if placements else 0
    sheet_area = sheets_used * float(sheet_length) * float(sheet_width)
    utilization = round(placed_area / sheet_area, 4) if sheet_area > 0 else 0.0
    waste = round(sheet_area - placed_area, 2)
    new_status = status
    if status == "completed" and requested_count and len(placements) < requested_count:
        new_status = "partial"
    return {
        "utilization_rate": utilization,
        "waste_area_mm2": waste,
        "sheets_used": sheets_used,
        "status": new_status,
        "placed_count": len(placements),
        "requested_count": requested_count,
        "placed_area_mm2": round(placed_area, 2),
    }


def _as_dict(v):
    if v is None:
        return None
    return v if isinstance(v, dict) else json.loads(v)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("""
        SELECT j.id, j.result_json, j.sheet_length_mm, j.sheet_width_mm,
               j.utilization_rate, j.total_waste_area_mm2, j.sheets_used, j.status,
               COALESCE((SELECT SUM(p.quantity) FROM nesting_parts p
                         WHERE p.nesting_job_id = j.id), 0) AS requested
        FROM nesting_jobs j
        WHERE j.result_json IS NOT NULL
    """)).fetchall()

    fixed = 0
    for r in rows:
        rj = _as_dict(r.result_json)
        if not rj or "legacy_v20" in rj:
            continue
        new = recompute(rj, r.sheet_length_mm, r.sheet_width_mm, int(r.requested), r.status)
        if new is None:
            continue
        rj["legacy_v20"] = {
            "utilization_rate": float(r.utilization_rate) if r.utilization_rate is not None else None,
            "waste_area_mm2": float(r.total_waste_area_mm2) if r.total_waste_area_mm2 is not None else None,
            "sheets_used": r.sheets_used,
            "status": r.status,
        }
        rj.update({k: new[k] for k in
                   ("utilization_rate", "waste_area_mm2", "sheets_used",
                    "placed_count", "requested_count", "placed_area_mm2")})
        conn.execute(sa.text("""
            UPDATE nesting_jobs
            SET utilization_rate = :u, total_waste_area_mm2 = :w, sheets_used = :s,
                status = :st, result_json = CAST(:rj AS JSONB)
            WHERE id = :id
        """), {"u": new["utilization_rate"], "w": new["waste_area_mm2"], "s": new["sheets_used"],
               "st": new["status"], "rj": json.dumps(rj, ensure_ascii=False), "id": r.id})
        fixed += 1
    print(f"[c3e8f1a2b4d5] nesting_jobs 利用率重算：{fixed} 筆")


def downgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, result_json FROM nesting_jobs WHERE result_json -> 'legacy_v20' IS NOT NULL"
    )).fetchall()
    for r in rows:
        rj = _as_dict(r.result_json)
        old = rj.pop("legacy_v20")
        for k in ("placed_count", "requested_count", "placed_area_mm2"):
            rj.pop(k, None)
        rj["utilization_rate"] = old["utilization_rate"]
        rj["waste_area_mm2"] = old["waste_area_mm2"]
        rj["sheets_used"] = old["sheets_used"]
        conn.execute(sa.text("""
            UPDATE nesting_jobs
            SET utilization_rate = :u, total_waste_area_mm2 = :w, sheets_used = :s,
                status = :st, result_json = CAST(:rj AS JSONB)
            WHERE id = :id
        """), {"u": old["utilization_rate"], "w": old["waste_area_mm2"], "s": old["sheets_used"],
               "st": old["status"], "rj": json.dumps(rj, ensure_ascii=False), "id": r.id})
