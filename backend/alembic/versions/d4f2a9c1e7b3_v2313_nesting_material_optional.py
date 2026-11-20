"""v2.3.13: nesting_jobs.material_id 改為可空

Revision ID: d4f2a9c1e7b3
Revises: c3e8f1a2b4d5
Create Date: 2026-11-20

為什麼：
  /erp/nesting 頁面沒有選物料的欄位，舊版前端永遠送假 UUID
  00000000-0000-0000-0000-000000000001。新安裝的資料庫沒有這筆物料，
  NOT NULL 外鍵讓「產生裁切計畫」直接 500。
  排版計算本身不需要物料；物料只用來把結果和庫存關聯，所以改為選填。

downgrade：
  改回 NOT NULL 前先檢查有沒有 material_id 為 NULL 的排版紀錄；
  有的話停下來並說明，不自動刪除使用者的排版歷史。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4f2a9c1e7b3"
down_revision: Union[str, None] = "c3e8f1a2b4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "nesting_jobs", "material_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    n = bind.execute(sa.text("SELECT count(*) FROM nesting_jobs WHERE material_id IS NULL")).scalar()
    if n:
        raise RuntimeError(
            f"有 {n} 筆排版紀錄沒有指定物料，無法改回 NOT NULL。"
            "請先為這些紀錄補上 material_id 或自行刪除後再 downgrade。"
        )
    op.alter_column(
        "nesting_jobs", "material_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
