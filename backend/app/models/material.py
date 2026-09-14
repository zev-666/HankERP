import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Numeric, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Material(Base):
    __tablename__ = "materials"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # 'acrylic','wood','metal','led','paint','hardware','other'
    material_type: Mapped[str] = mapped_column(String(50))
    # 壓克力專屬
    thickness_mm: Mapped[Decimal] = mapped_column(Numeric(5,2), nullable=True)
    color: Mapped[str] = mapped_column(String(100), nullable=True)   # '透明','白色','黑色','霧面'
    standard_length_mm: Mapped[Decimal] = mapped_column(Numeric(8,2), default=Decimal("2000"))
    standard_width_mm: Mapped[Decimal] = mapped_column(Numeric(8,2), default=Decimal("1000"))
    # 通用
    unit: Mapped[str] = mapped_column(String(20), default="片")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12,4), default=Decimal("0"))
    cost_per_cai: Mapped[Decimal] = mapped_column(Numeric(12,4), nullable=True)   # 每才成本
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    min_stock_qty: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class SheetStock(Base):
    """壓克力板材庫存（含剩料追蹤）"""
    __tablename__ = "sheet_stocks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    batch_no: Mapped[str] = mapped_column(String(100), nullable=True)
    actual_length_mm: Mapped[Decimal] = mapped_column(Numeric(8,2))
    actual_width_mm: Mapped[Decimal] = mapped_column(Numeric(8,2))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    is_remnant: Mapped[bool] = mapped_column(Boolean, default=False)
    remnant_grade: Mapped[str] = mapped_column(String(10), nullable=True)  # A/B/C
    parent_stock_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sheet_stocks.id"), nullable=True)
    source_wo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    location_code: Mapped[str] = mapped_column(String(50), nullable=True)
    # 'available','reserved','used','scrapped'
    status: Mapped[str] = mapped_column(String(20), default="available")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    material: Mapped["Material"] = relationship("Material", lazy="joined")
