import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Integer, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    po_number: Mapped[str] = mapped_column(String(30), unique=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    # draft/sent/confirmed/received/closed
    status: Mapped[str] = mapped_column(String(20), default="draft")
    order_date: Mapped[date] = mapped_column(Date, default=date.today)
    expected_date: Mapped[date] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(10), default="TWD")
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    items: Mapped[list["PoItem"]] = relationship("PoItem", back_populates="po", lazy="select")

class PoItem(Base):
    __tablename__ = "po_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    line_no: Mapped[int] = mapped_column(Integer)
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(12,4))
    received_qty: Mapped[Decimal] = mapped_column(Numeric(12,4), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,4))
    unit: Mapped[str] = mapped_column(String(20))
    # 壓克力板材專屬欄位
    sheet_thickness_mm: Mapped[Decimal] = mapped_column(Numeric(5,2), nullable=True)
    sheet_length_mm: Mapped[Decimal] = mapped_column(Numeric(8,2), nullable=True)
    sheet_width_mm: Mapped[Decimal] = mapped_column(Numeric(8,2), nullable=True)
    sheet_color: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    po: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="items")
