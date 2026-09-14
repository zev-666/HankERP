"""v2.0: 線上詢價表 + 成品(FG)庫存支援 + 工單完工數量

Revision ID: b2d7a1c94e30
Revises: 8f512cecc226
Create Date: 2026-09-14

三件事：
1. 新增 inquiries 表——官網詢價表單先前送出後資料直接消失，沒有任何地方存。
2. inventory_balances / inventory_transactions 新增 product_id 並把 material_id 改為可空，
   讓「成品」也能有庫存。原 schema 只認得 materials，導致工單完工入庫在資料模型上做不出來。
   以 CHECK 約束保證 material_id / product_id 恰有一個有值。
3. work_orders 新增 completed_qty，記錄實際完工入庫數（可與計畫數不同）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2d7a1c94e30"
down_revision: Union[str, None] = "8f512cecc226"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. 線上詢價
    op.create_table(
        "inquiries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("company", sa.String(200), nullable=True),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("product_type", sa.String(100), nullable=True),
        sa.Column("quantity", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("converted_customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("source_page", sa.String(200), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    # 後台最常用的查詢是「依狀態撈、依時間排」，建複合索引
    op.create_index("ix_inquiries_status_created", "inquiries", ["status", "created_at"])

    # ── 2. 成品庫存支援
    for table in ("inventory_balances", "inventory_transactions"):
        op.add_column(
            table,
            sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        )
        op.alter_column(table, "material_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
        op.create_check_constraint(
            f"ck_{table}_material_xor_product",
            table,
            "(material_id IS NOT NULL AND product_id IS NULL) "
            "OR (material_id IS NULL AND product_id IS NOT NULL)",
        )

    # ── 3. 工單完工數量
    op.add_column(
        "work_orders",
        sa.Column("completed_qty", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("work_orders", "completed_qty")
    for table in ("inventory_transactions", "inventory_balances"):
        op.drop_constraint(f"ck_{table}_material_xor_product", table, type_="check")
        op.alter_column(table, "material_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
        op.drop_column(table, "product_id")
    op.drop_index("ix_inquiries_status_created", table_name="inquiries")
    op.drop_table("inquiries")
