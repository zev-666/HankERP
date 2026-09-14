import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Numeric, Integer, Text, Date
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=True)
    # standard/custom/semi
    product_type: Mapped[str] = mapped_column(String(50), default="custom")
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(Text, nullable=True)
    standard_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    list_price: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    unit: Mapped[str] = mapped_column(String(20), default="台")
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    boms: Mapped[list["BomHeader"]] = relationship("BomHeader", back_populates="product", lazy="select")

class BomHeader(Base):
    __tablename__ = "bom_headers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    # draft/active/obsolete
    status: Mapped[str] = mapped_column(String(20), default="draft")
    effective_date: Mapped[date] = mapped_column(Date, nullable=True)
    expire_date: Mapped[date] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    product: Mapped["Product"] = relationship("Product", back_populates="boms")
    items: Mapped[list["BomItem"]] = relationship("BomItem", back_populates="bom", lazy="select")

class BomItem(Base):
    __tablename__ = "bom_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bom_headers.id"))
    line_no: Mapped[int] = mapped_column(Integer)
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12,4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20))
    wastage_rate: Mapped[Decimal] = mapped_column(Numeric(5,4), default=Decimal("0.05"))
    cut_length_mm: Mapped[Decimal] = mapped_column(Numeric(10,2), nullable=True)
    cut_width_mm: Mapped[Decimal] = mapped_column(Numeric(10,2), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    substitute_material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    bom: Mapped["BomHeader"] = relationship("BomHeader", back_populates="items")
