import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Numeric, Integer, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Quotation(Base):
    __tablename__ = "quotations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    quote_number: Mapped[str] = mapped_column(String(30), unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"))
    # draft/sent/accepted/rejected/expired
    status: Mapped[str] = mapped_column(String(20), default="draft")
    valid_until: Mapped[date] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="TWD")
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_confidence: Mapped[Decimal] = mapped_column(Numeric(5,4), nullable=True)
    material_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    processing_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    overhead_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(5,4), default=Decimal("0.35"))
    final_price: Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal("0"))
    won_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    lost_reason: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    items: Mapped[list["QuotationItem"]] = relationship("QuotationItem", back_populates="quotation", lazy="select")

class QuotationItem(Base):
    __tablename__ = "quotation_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotations.id"))
    line_no: Mapped[int] = mapped_column(Integer)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    acrylic_cai: Mapped[Decimal] = mapped_column(Numeric(8,4), nullable=True)
    cnc_minutes: Mapped[Decimal] = mapped_column(Numeric(8,2), nullable=True)
    laser_meters: Mapped[Decimal] = mapped_column(Numeric(8,2), nullable=True)
    assembly_hours: Mapped[Decimal] = mapped_column(Numeric(6,2), nullable=True)
    quotation: Mapped["Quotation"] = relationship("Quotation", back_populates="items")
