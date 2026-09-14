import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Integer, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class WorkOrder(Base):
    __tablename__ = "work_orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    wo_number: Mapped[str] = mapped_column(String(30), unique=True)
    sales_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bom_headers.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # draft/released/in_progress/completed/closed
    status: Mapped[str] = mapped_column(String(20), default="draft")
    priority: Mapped[int] = mapped_column(Integer, default=5)
    planned_start: Mapped[date] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date] = mapped_column(Date, nullable=True)
    actual_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # v2.0：完工入庫實際良品數量（可分批入庫，累加）
    completed_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    operations: Mapped[list["WoOperation"]] = relationship("WoOperation", back_populates="work_order", lazy="select")
    material_issues: Mapped[list["WoMaterialIssue"]] = relationship("WoMaterialIssue", back_populates="work_order", lazy="select")

class WoOperation(Base):
    __tablename__ = "wo_operations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("work_orders.id"))
    op_seq: Mapped[int] = mapped_column(Integer)
    op_name: Mapped[str] = mapped_column(String(100))
    machine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=True)
    setup_time_min: Mapped[int] = mapped_column(Integer, default=0)
    run_time_per_unit_min: Mapped[Decimal] = mapped_column(Numeric(8,2), default=Decimal("0"))
    # pending/in_progress/completed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    actual_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    operator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    good_qty: Mapped[int] = mapped_column(Integer, default=0)
    scrap_qty: Mapped[int] = mapped_column(Integer, default=0)
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="operations")

class WoMaterialIssue(Base):
    __tablename__ = "wo_material_issues"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("work_orders.id"))
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    sheet_stock_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sheet_stocks.id"), nullable=True)
    planned_qty: Mapped[Decimal] = mapped_column(Numeric(12,4))
    issued_qty: Mapped[Decimal] = mapped_column(Numeric(12,4), default=Decimal("0"))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="material_issues")
