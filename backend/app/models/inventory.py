import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Text, BigInteger, Computed
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class InventoryBalance(Base):
    __tablename__ = "inventory_balances"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    # v2.0：material_id 改為可空，並新增 product_id。
    # 原因：完工入庫（FG倉）存放的是「成品」，成品在本系統屬 products 主檔而非 materials 主檔，
    # 原本的 schema 無法表達成品庫存，導致「工單完工入庫」這個功能在資料模型上根本做不出來。
    # 兩者恰有一個為 NOT NULL（由 CHECK 約束保證），等同一個輕量的 item master。
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    # RAW/WIP/FG/REMNANT/SCRAP
    warehouse_code: Mapped[str] = mapped_column(String(20), default="RAW")
    location_code: Mapped[str] = mapped_column(String(50), nullable=True)
    qty_on_hand: Mapped[Decimal] = mapped_column(Numeric(14,4), default=Decimal("0"))
    qty_reserved: Mapped[Decimal] = mapped_column(Numeric(14,4), default=Decimal("0"))
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def qty_available(self) -> Decimal:
        return self.qty_on_hand - self.qty_reserved

class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    # RECEIPT/ISSUE/TRANSFER/ADJUST/SCRAP
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # v2.0：同 InventoryBalance，成品異動記在 product_id，物料異動記在 material_id
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    warehouse_code: Mapped[str] = mapped_column(String(20))
    qty: Mapped[Decimal] = mapped_column(Numeric(14,4), nullable=False)  # 正=入庫 負=出庫
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12,4), nullable=True)
    # PO/WO/SO/MANUAL
    source_type: Mapped[str] = mapped_column(String(30), nullable=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    lot_number: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
