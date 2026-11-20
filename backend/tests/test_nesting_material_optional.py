"""
裁切排版不指定物料也要能算（v2.3.13）。

舊行為：/erp/nesting 頁面沒有任何選物料的欄位，`material_id` 永遠送假值
`00000000-0000-0000-0000-000000000001`。nesting_jobs.material_id 是 NOT NULL
外鍵，新安裝（離線版、剛 seed 完）的資料庫裡沒有這筆物料，
按「產生裁切計畫」就是 ForeignKeyViolation → 500。

2026-11-20 製作使用教學時在乾淨資料庫上重現：前端按鈕無反應、uvicorn log
出現 nesting_jobs_material_id_fkey。

這四支測試在舊程式上都會失敗（已實際驗證）：
  1. NestingRequest 少了 material_id → ValidationError
  2. NestingJob.material_id 的 nullable 是 False
  3. alembic 沒有把欄位改成可空的 migration
  4. page.tsx 還寫著假 UUID
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.nesting import NestingJob  # noqa: E402
from app.modules.nesting.schemas import NestingRequest  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
MIGRATION = BACKEND / "alembic" / "versions" / "d4f2a9c1e7b3_v2313_nesting_material_optional.py"


def test_request_without_material_is_valid():
    req = NestingRequest(parts=[{"label": "背板", "length_mm": 630, "width_mm": 300, "quantity": 2}])
    assert req.material_id is None


def test_model_column_is_nullable():
    assert NestingJob.__table__.c.material_id.nullable is True


def test_migration_makes_column_nullable_and_is_head():
    assert MIGRATION.exists(), "缺少 v2.3.13 migration"
    spec = importlib.util.spec_from_file_location("m", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.down_revision == "c3e8f1a2b4d5"
    src = MIGRATION.read_text(encoding="utf-8")
    assert "nullable=True" in src and "nullable=False" in src  # upgrade 與 downgrade 都有寫


def test_page_no_longer_sends_placeholder_uuid():
    page = (REPO / "frontend" / "src" / "app" / "erp" / "nesting" / "page.tsx").read_text(encoding="utf-8")
    assert "00000000-0000-0000-0000-000000000001" not in page
