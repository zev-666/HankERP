import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Integer, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # cnc/laser/saw/spray/drill/polish/assembly
    equipment_type: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=True)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(8,2), default=Decimal("0"))
    power_kw: Mapped[Decimal] = mapped_column(Numeric(6,2), nullable=True)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=True)
    warranty_expire: Mapped[date] = mapped_column(Date, nullable=True)
    # active/maintenance/breakdown/retired
    status: Mapped[str] = mapped_column(String(20), default="active")
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.id"))
    # preventive/corrective/inspection
    maintenance_type: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    technician: Mapped[str] = mapped_column(String(100), nullable=True)
    cost: Mapped[Decimal] = mapped_column(Numeric(10,2), nullable=True)
    downtime_hours: Mapped[Decimal] = mapped_column(Numeric(6,2), nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_maintenance_date: Mapped[date] = mapped_column(Date, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
