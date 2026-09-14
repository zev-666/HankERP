from uuid import UUID
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.models.inventory import InventoryBalance, InventoryTransaction
from app.models.material import SheetStock
from app.models.nesting import RemnantInventory
from app.modules.inventory.schemas import TransactionCreate, SheetStockCreate, RemnantCreate

class InventoryService:

    async def get_balances(self, db: AsyncSession, tenant_id: UUID,
                           warehouse_code: str = None, material_id: UUID = None):
        q = select(InventoryBalance).where(InventoryBalance.tenant_id == tenant_id)
        if warehouse_code:
            q = q.where(InventoryBalance.warehouse_code == warehouse_code)
        if material_id:
            q = q.where(InventoryBalance.material_id == material_id)
        result = await db.execute(q)
        return result.scalars().all()

    async def create_transaction(self, db: AsyncSession, tenant_id: UUID,
                                  user_id: UUID, data: TransactionCreate,
                                  transaction_type: str = "RECEIPT"):
        # 1. 建立異動記錄
        txn = InventoryTransaction(
            tenant_id=tenant_id,
            transaction_type=transaction_type,
            material_id=data.material_id,
            warehouse_code=data.warehouse_code,
            qty=data.qty,
            unit_cost=data.unit_cost,
            source_type=data.source_type,
            source_id=data.source_id,
            lot_number=data.lot_number,
            notes=data.notes,
            created_by=user_id,
        )
        db.add(txn)

        # 2. 更新餘額
        q = select(InventoryBalance).where(
            InventoryBalance.tenant_id == tenant_id,
            InventoryBalance.material_id == data.material_id,
            InventoryBalance.warehouse_code == data.warehouse_code,
        )
        result = await db.execute(q)
        balance = result.scalar_one_or_none()

        if balance:
            balance.qty_on_hand += data.qty
            balance.last_updated = datetime.utcnow()
        else:
            balance = InventoryBalance(
                tenant_id=tenant_id,
                material_id=data.material_id,
                warehouse_code=data.warehouse_code,
                qty_on_hand=data.qty,
            )
            db.add(balance)

        await db.flush()
        return txn

    async def get_sheets(self, db: AsyncSession, tenant_id: UUID,
                         material_id: UUID = None, is_remnant: bool = None):
        q = select(SheetStock).where(
            SheetStock.tenant_id == tenant_id,
            SheetStock.status == "available",
        )
        if material_id:
            q = q.where(SheetStock.material_id == material_id)
        if is_remnant is not None:
            q = q.where(SheetStock.is_remnant == is_remnant)
        result = await db.execute(q)
        return result.scalars().all()

    async def receive_sheets(self, db: AsyncSession, tenant_id: UUID,
                              user_id: UUID, data: SheetStockCreate):
        sheet = SheetStock(
            tenant_id=tenant_id,
            material_id=data.material_id,
            batch_no=data.batch_no,
            actual_length_mm=data.actual_length_mm,
            actual_width_mm=data.actual_width_mm,
            quantity=data.quantity,
            location_code=data.location_code,
            is_remnant=False,
        )
        db.add(sheet)
        # 同步更新庫存餘額
        txn_data = TransactionCreate(
            material_id=data.material_id,
            warehouse_code="RAW",
            qty=Decimal(str(data.quantity)),
        )
        await self.create_transaction(db, tenant_id, user_id, txn_data, "RECEIPT")
        await db.flush()
        return sheet

    async def add_remnant(self, db: AsyncSession, tenant_id: UUID, data: RemnantCreate):
        remnant = RemnantInventory(
            tenant_id=tenant_id,
            material_id=data.material_id,
            nesting_job_id=data.nesting_job_id,
            length_mm=data.length_mm,
            width_mm=data.width_mm,
            grade=data.grade,
            location_code=data.location_code,
            notes=data.notes,
        )
        db.add(remnant)
        await db.flush()
        return remnant

    async def get_remnants(self, db: AsyncSession, tenant_id: UUID,
                            material_id: UUID = None, min_length: float = 0, min_width: float = 0):
        q = select(RemnantInventory).where(
            RemnantInventory.tenant_id == tenant_id,
            RemnantInventory.status == "available",
        )
        if material_id:
            q = q.where(RemnantInventory.material_id == material_id)
        if min_length:
            q = q.where(RemnantInventory.length_mm >= min_length)
        if min_width:
            q = q.where(RemnantInventory.width_mm >= min_width)
        result = await db.execute(q)
        return result.scalars().all()

    async def get_low_stock_alerts(self, db: AsyncSession, tenant_id: UUID):
        """回傳低於安全庫存的物料清單"""
        from app.models.material import Material
        from sqlalchemy import and_
        # Join materials with balances and filter below min_stock_qty
        q = (
            select(Material, InventoryBalance)
            .outerjoin(InventoryBalance, and_(
                InventoryBalance.material_id == Material.id,
                InventoryBalance.tenant_id == tenant_id,
                InventoryBalance.warehouse_code == "RAW",
            ))
            .where(Material.tenant_id == tenant_id, Material.is_active == True)
        )
        result = await db.execute(q)
        rows = result.all()
        alerts = []
        for mat, bal in rows:
            on_hand = bal.qty_on_hand if bal else Decimal("0")
            if mat.min_stock_qty > 0 and on_hand < mat.min_stock_qty:
                alerts.append({
                    "material_id": str(mat.id),
                    "material_name": mat.name,
                    "on_hand": float(on_hand),
                    "min_stock_qty": float(mat.min_stock_qty),
                    "shortage": float(mat.min_stock_qty - on_hand),
                })
        return alerts
