"""
驗證 migration c3e8f1a2b4d5（v2.1 nesting_jobs 歷史利用率修正）真的改對資料庫。

流程（需要已經 `alembic upgrade head` ＋ `seed_data.py` 的資料庫）：
  1. alembic downgrade 到 b2d7a1c94e30（修正前）
  2. 用舊引擎的輸出格式寫入 3 筆 nesting_jobs：
       A 整板件排不下：舊版回報 utilization 1.0         → 應變 0、sheets 0、partial
       B 5 件只排進 4 件：舊版回報 0.45                 → 應變 0.3、partial
       C pending、沒有 result_json                      → 不可被動到
  3. alembic upgrade head → 直接查資料庫比對
  4. downgrade → 應還原舊值；再 upgrade → 應再次修正（備份不會被覆蓋）
  5. 刪除測試資料

用法：cd backend && python scripts/verify_migration_v21.py
CI（.github/workflows/ci.yml）在 seed 之後、pytest 之前執行。
"""
import asyncio
import json
import os
import subprocess
import sys
import uuid

import asyncpg

PRE = "b2d7a1c94e30"
DSN = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
FAIL = []


def alembic(*args):
    print("$ alembic", *args, flush=True)
    subprocess.run(["alembic", *args], check=True)


def check(name, got, want):
    ok = got == want
    print(f"  {'✓' if ok else '✗'} {name}: {got!r}" + ("" if ok else f"（應為 {want!r}）"))
    if not ok:
        FAIL.append(name)


async def fetch(conn, jid):
    r = await conn.fetchrow(
        "SELECT utilization_rate, total_waste_area_mm2, sheets_used, status, result_json "
        "FROM nesting_jobs WHERE id=$1", jid)
    rj = r["result_json"]
    rj = json.loads(rj) if isinstance(rj, str) else rj
    return (float(r["utilization_rate"]) if r["utilization_rate"] is not None else None,
            float(r["total_waste_area_mm2"]) if r["total_waste_area_mm2"] is not None else None,
            r["sheets_used"], r["status"], rj)


async def main():
    alembic("downgrade", PRE)
    conn = await asyncpg.connect(DSN)
    tenant = await conn.fetchval("SELECT id FROM tenants WHERE slug='guishan-acrylic'")
    assert tenant, "找不到 seed 租戶，請先跑 scripts/seed_data.py"
    mat = uuid.uuid4()
    await conn.execute(
        "INSERT INTO materials (id, tenant_id, code, name, material_type, standard_length_mm, "
        "standard_width_mm, unit, unit_cost, min_stock_qty, reorder_point, is_active, created_at) "
        "VALUES ($1,$2,$3,'CI 測試板','acrylic',2000,1000,'sheet',0,0,0,true,now())",
        mat, tenant, f"CI-{mat.hex[:8]}")

    ja, jb, jc = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    async def job(jid, util, waste, sheets, status, rj, parts):
        await conn.execute(
            "INSERT INTO nesting_jobs (id, tenant_id, material_id, sheet_length_mm, sheet_width_mm, "
            "kerf_mm, algorithm_version, utilization_rate, total_waste_area_mm2, sheets_used, "
            "result_json, status, created_at) "
            "VALUES ($1,$2,$3,2000,1000,3,'bfd_v1',$4,$5,$6,$7::jsonb,$8,now())",
            jid, tenant, mat, util, waste, sheets,
            json.dumps(rj) if rj is not None else None, status)
        for label, qty in parts:
            await conn.execute(
                "INSERT INTO nesting_parts (id, nesting_job_id, label, part_length_mm, part_width_mm, "
                "quantity, can_rotate) VALUES ($1,$2,$3,100,100,$4,true)",
                uuid.uuid4(), jid, label, qty)

    await job(ja, 1.0, 0, 1, "completed",
              {"sheets_used": 1, "utilization_rate": 1.0, "placements": [], "waste_area_mm2": 0,
               "remnants": []}, [("整板件", 1)])
    pl = [{"part_id": "ok", "label": "ok", "sheet_index": 0, "x": 0, "y": 0,
           "placed_length": 500, "placed_width": 300, "rotated": False}] * 4
    await job(jb, 0.45, 1100000, 1, "completed",
              {"sheets_used": 1, "utilization_rate": 0.45, "placements": pl,
               "waste_area_mm2": 1100000, "remnants": []}, [("big", 1), ("ok", 4)])
    await job(jc, None, None, None, "pending", None, [])
    await conn.close()

    try:
        alembic("upgrade", "head")
        conn = await asyncpg.connect(DSN)
        print("[upgrade 後]")
        u, w, s, st, rj = await fetch(conn, ja)
        check("A 利用率", u, 0.0); check("A 板數", s, 0); check("A 狀態", st, "partial")
        check("A 備份舊利用率", rj["legacy_v20"]["utilization_rate"], 1.0)
        u, w, s, st, rj = await fetch(conn, jb)
        check("B 利用率", u, 0.3); check("B 廢料", w, 1400000.0); check("B 狀態", st, "partial")
        check("B placed_count", rj["placed_count"], 4); check("B requested_count", rj["requested_count"], 5)
        u, w, s, st, rj = await fetch(conn, jc)
        check("C 未被動到", (u, s, st, rj), (None, None, "pending", None))
        await conn.close()

        alembic("downgrade", PRE)
        conn = await asyncpg.connect(DSN)
        print("[downgrade 後]")
        u, w, s, st, rj = await fetch(conn, ja)
        check("A 還原利用率", u, 1.0); check("A 還原狀態", st, "completed")
        check("A 備份已移除", "legacy_v20" in rj, False)
        u, w, s, st, rj = await fetch(conn, jb)
        check("B 還原利用率", u, 0.45)
        await conn.close()

        alembic("upgrade", "head")
        conn = await asyncpg.connect(DSN)
        print("[再次 upgrade 後]")
        u, w, s, st, rj = await fetch(conn, jb)
        check("B 再修正利用率", u, 0.3)
        check("B 備份仍是原始舊值", rj["legacy_v20"]["utilization_rate"], 0.45)
    finally:
        conn = await asyncpg.connect(DSN)
        await conn.execute("DELETE FROM nesting_parts WHERE nesting_job_id = ANY($1::uuid[])", [ja, jb, jc])
        await conn.execute("DELETE FROM nesting_jobs WHERE id = ANY($1::uuid[])", [ja, jb, jc])
        await conn.execute("DELETE FROM materials WHERE id=$1", mat)
        await conn.close()
        # 確保資料庫停在 head，不影響後續 CI 步驟
        alembic("upgrade", "head")

    if FAIL:
        print(f"✗ migration 驗證失敗 {len(FAIL)} 項：{FAIL}")
        sys.exit(1)
    print("✓ migration c3e8f1a2b4d5 驗證全部通過")


if __name__ == "__main__":
    asyncio.run(main())
