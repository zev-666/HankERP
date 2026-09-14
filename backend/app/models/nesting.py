import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class NestingJob(Base):
    __tablename__ = "nesting_jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    wo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=True)
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    sheet_length_mm: Mapped[Decimal] = mapped_column(Numeric(8,2), default=Decimal("2000"))
    sheet_width_mm: Mapped[Decimal] = mapped_column(Numeric(8,2), default=Decimal("1000"))
    kerf_mm: Mapped[Decimal] = mapped_column(Numeric(4,1), default=Decimal("3"))
    algorithm_version: Mapped[str] = mapped_column(String(20), default="bfd_v1")
    utilization_rate: Mapped[Decimal] = mapped_column(Numeric(5,4), nullable=True)
    total_waste_area_mm2: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=True)
    sheets_used: Mapped[int] = mapped_column(Integer, nullable=True)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # pending/running/completed/failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    celery_task_id: Mapped[str] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    parts: Mapped[list["NestingPart"]] = relationship("NestingPart", back_populates="job", lazy="select")

class NestingPart(Base):
    __tablename__ = "nesting_parts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nesting_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nesting_jobs.id"))
    bom_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bom_items.id"), nullable=True)
    label: Mapped[str] = mapped_column(String(100), nullable=True)
    part_length_mm: Mapped[Decimal] = mapped_column(Numeric(8,2))
    part_width_mm: Mapped[Decimal] = mapped_column(Numeric(8,2))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    can_rotate: Mapped[bool] = mapped_column(Boolean, default=True)
    job: Mapped["NestingJob"] = relationship("NestingJob", back_populates="parts")

class NestingPlacement(Base):
    __tablename__ = "nesting_placements"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nesting_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nesting_jobs.id"))
    sheet_index: Mapped[int] = mapped_column(Integer)
    part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nesting_parts.id"))
    x_mm: Mapped[Decimal] = mapped_column(Numeric(8,2))
    y_mm: Mapped[Decimal] = mapped_column(Numeric(8,2))
    rotated: Mapped[bool] = mapped_column(Boolean, default=False)
    cutting_path_json: Mapped[dict] = mapped_column(JSONB, nullable=True)

class RemnantInventory(Base):
    __tablename__ = "remnant_inventory"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    nesting_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nesting_jobs.id"), nullable=True)
    length_mm: Mapped[Decimal] = mapped_column(Numeric(8,2))
    width_mm: Mapped[Decimal] = mapped_column(Numeric(8,2))
    grade: Mapped[str] = mapped_column(String(10), default="A")
    location_code: Mapped[str] = mapped_column(String(50), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    # available/reserved/used/scrapped
    status: Mapped[str] = mapped_column(String(20), default="available")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    @property
    def area_mm2(self) -> Decimal:
        return self.length_mm * self.width_mm
