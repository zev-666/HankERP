"""
官網線上詢價（Inquiry）— 官網訪客填寫的詢價需求。

設計說明：
- 這是官網唯一「未登入也能寫入資料庫」的入口，因此 router 端必須套用 rate limit，
  且此表所有欄位皆為使用者輸入，不得直接信任（僅做長度限制與基本格式驗證）。
- tenant_id 於建立時由後端依 settings/預設租戶填入，不由前端傳入，避免跨租戶寫入。
- 詢價轉為正式客戶後，以 converted_customer_id 建立關聯，保留原始詢價內容供追溯。
"""
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)

    # 聯絡資訊（官網訪客填寫）
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)

    # 需求內容
    product_type: Mapped[str] = mapped_column(String(100), nullable=True)
    quantity: Mapped[str] = mapped_column(String(100), nullable=True)  # 自由文字，例如「約100台」
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # 業務處理狀態：new（新進）/ contacted（已聯繫）/ quoted（已報價）/ won（成交）/ lost（未成交）/ spam
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    assigned_to: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    internal_notes: Mapped[str] = mapped_column(Text, nullable=True)
    converted_customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    # 來源追溯（供行銷分析，非個資用途）
    source_page: Mapped[str] = mapped_column(String(200), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
