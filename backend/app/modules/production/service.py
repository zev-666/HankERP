from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.production import WorkOrder, WoOperation, WoMaterialIssue
from app.models.product import BomHeader, BomItem
from app.models.inventory import InventoryBalance, InventoryTransaction
from app.modules.production.schemas import WorkOrderCreate


class InsufficientStockError(Exception):
    """發料時庫存不足。shortages 帶回每項缺料的需求量/現有量，供前端直接顯示給倉管。"""

    def __init__(self, shortages: list[dict]):
        self.shortages = shortages
        super().__init__("庫存不足，無法發料")

async def _next_wo_number(db: AsyncSession) -> str:
    year = date.today().year
    q = select(func.count(WorkOrder.id)).where(WorkOrder.wo_number.like(f"WO{year}-%"))
    count = (await db.execute(q)).scalar() or 0
    return f"WO{year}-{count+1:04d}"

class ProductionService:

    async def create_work_order(self, db: AsyncSession, tenant_id: UUID,
                                 user_id: UUID, data: WorkOrderCreate) -> WorkOrder:
        wo_number = await _next_wo_number(db)
        wo = WorkOrder(
            tenant_id=tenant_id,
            wo_number=wo_number,
            product_id=data.product_id,
            bom_id=data.bom_id,
            quantity=data.quantity,
            priority=data.priority,
            planned_start=data.planned_start,
            planned_end=data.planned_end,
            notes=data.notes,
            created_by=user_id,
        )
        db.add(wo)
        await db.flush()

        # 建立工序
        for op_data in data.operations:
            op = WoOperation(
                wo_id=wo.id,
                op_seq=op_data.op_seq,
                op_name=op_data.op_name,
                machine_id=op_data.machine_id,
                setup_time_min=op_data.setup_time_min,
                run_time_per_unit_min=op_data.run_time_per_unit_min,
            )
            db.add(op)

        # 若有BOM，自動展開備料清單
        if data.bom_id:
            bom_q = select(BomItem).where(BomItem.bom_id == data.bom_id)
            result = await db.execute(bom_q)
            bom_items = result.scalars().all()
            for item in bom_items:
                planned_qty = item.quantity * data.quantity * (1 + item.wastage_rate)
                issue = WoMaterialIssue(
                    wo_id=wo.id,
                    material_id=item.material_id,
                    planned_qty=planned_qty,
                )
                db.add(issue)

        await db.flush()
        return wo

    async def get_work_order_detail(self, db: AsyncSession, wo_id: UUID, tenant_id: UUID):
        from sqlalchemy.orm import selectinload
        q = select(WorkOrder).options(
            selectinload(WorkOrder.operations)
        ).where(WorkOrder.id == wo_id, WorkOrder.tenant_id == tenant_id)
        result = await db.execute(q)
        return result.scalar_one_or_none()

    async def list_work_orders(self, db: AsyncSession, tenant_id: UUID,
                                status: str = None):
        q = select(WorkOrder).where(WorkOrder.tenant_id == tenant_id)
        if status:
            q = q.where(WorkOrder.status == status)
        q = q.order_by(WorkOrder.priority.asc(), WorkOrder.planned_end.asc())
        result = await db.execute(q)
        return result.scalars().all()

    async def release_work_order(self, db: AsyncSession, wo_id: UUID, tenant_id: UUID):
        q = select(WorkOrder).where(WorkOrder.id == wo_id, WorkOrder.tenant_id == tenant_id)
        result = await db.execute(q)
        wo = result.scalar_one_or_none()
        if wo and wo.status == "draft":
            wo.status = "released"
        return wo

    async def start_operation(self, db: AsyncSession, wo_id: UUID, op_id: UUID,
                               operator_id: UUID):
        q = select(WoOperation).where(WoOperation.id == op_id, WoOperation.wo_id == wo_id)
        result = await db.execute(q)
        op = result.scalar_one_or_none()
        if op:
            op.status = "in_progress"
            op.actual_start = datetime.utcnow()
            op.operator_id = operator_id
            # 若工單還是released，改為in_progress
            wo_q = select(WorkOrder).where(WorkOrder.id == wo_id)
            wo_res = await db.execute(wo_q)
            wo = wo_res.scalar_one_or_none()
            if wo and wo.status == "released":
                wo.status = "in_progress"
                wo.actual_start = datetime.utcnow()
        return op

    async def complete_operation(self, db: AsyncSession, wo_id: UUID, op_id: UUID,
                                  good_qty: int, scrap_qty: int):
        q = select(WoOperation).where(WoOperation.id == op_id, WoOperation.wo_id == wo_id)
        result = await db.execute(q)
        op = result.scalar_one_or_none()
        if op:
            op.status = "completed"
            op.actual_end = datetime.utcnow()
            op.good_qty = good_qty
            op.scrap_qty = scrap_qty
        return op

    async def get_material_plan(self, db: AsyncSession, wo_id: UUID):
        q = select(WoMaterialIssue).where(WoMaterialIssue.wo_id == wo_id)
        result = await db.execute(q)
        return result.scalars().all()

    # ── v2.0 新增：工單發料（扣庫存）與完工入庫 ───────────────────────────
    # 這兩支是 MVP_CHECKLIST 自己標為「最高優先」的斷點：在此之前，
    # 生產模組與庫存模組各自運作正常，但兩者從未串接——工單領了料，
    # 庫存數字不會動；工單完工，成品不會進 FG 倉。

    async def issue_materials(self, db: AsyncSession, wo_id: UUID, tenant_id: UUID,
                              user_id: UUID, warehouse_code: str = "RAW"):
        """
        依工單備料清單（wo_material_issues）扣減原料庫存。

        設計決策：
        - 先「全部檢查」再「全部扣帳」。任何一項不足就整批拒絕並回報缺料清單，
          不做部分發料——部分發料會讓現場拿到不完整的料，且資料庫留下難以回溯的半成狀態。
        - 只發尚未發足的差額（planned_qty - issued_qty），因此重複呼叫是安全的：
          已發足的工單再呼叫一次，回傳 issued 為空清單而非重複扣帳。
        """
        wo = (await db.execute(
            select(WorkOrder).where(WorkOrder.id == wo_id, WorkOrder.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if not wo:
            return None
        if wo.status not in ("released", "in_progress"):
            raise ValueError(f"工單狀態為 {wo.status}，僅「已發佈」或「生產中」的工單可以發料")

        issues = (await db.execute(
            select(WoMaterialIssue).where(WoMaterialIssue.wo_id == wo_id)
        )).scalars().all()
        if not issues:
            raise ValueError("此工單沒有備料清單（建立工單時未指定BOM，或BOM無材料項）")

        # ── 第一階段：檢查全部庫存是否足夠
        pending: list[tuple[WoMaterialIssue, InventoryBalance, Decimal]] = []
        shortages: list[dict] = []
        for issue in issues:
            need = Decimal(issue.planned_qty) - Decimal(issue.issued_qty)
            if need <= 0:
                continue
            balance = (await db.execute(
                select(InventoryBalance).where(
                    InventoryBalance.tenant_id == tenant_id,
                    InventoryBalance.material_id == issue.material_id,
                    InventoryBalance.warehouse_code == warehouse_code,
                )
            )).scalar_one_or_none()
            on_hand = Decimal(balance.qty_on_hand) if balance else Decimal("0")
            if on_hand < need:
                shortages.append({
                    "material_id": str(issue.material_id),
                    "required_qty": float(need),
                    "on_hand_qty": float(on_hand),
                    "shortage_qty": float(need - on_hand),
                })
            else:
                pending.append((issue, balance, need))

        if shortages:
            raise InsufficientStockError(shortages)

        # ── 第二階段：實際扣帳（此時已確定每一項都夠）
        issued_lines = []
        now = datetime.utcnow()
        for issue, balance, need in pending:
            balance.qty_on_hand = Decimal(balance.qty_on_hand) - need
            balance.last_updated = now
            db.add(InventoryTransaction(
                tenant_id=tenant_id,
                transaction_type="ISSUE",
                material_id=issue.material_id,
                warehouse_code=warehouse_code,
                qty=-need,                       # 負數＝出庫，與庫存模組既有慣例一致
                source_type="WO",
                source_id=wo_id,
                notes=f"工單 {wo.wo_number} 發料",
                created_by=user_id,
            ))
            issue.issued_qty = Decimal(issue.issued_qty) + need
            issue.issued_at = now
            issue.issued_by = user_id
            issued_lines.append({
                "material_id": str(issue.material_id),
                "issued_qty": float(need),
                "balance_after": float(balance.qty_on_hand),
            })

        await db.flush()
        return {"wo_number": wo.wo_number, "issued": issued_lines}

    async def complete_work_order(self, db: AsyncSession, wo_id: UUID, tenant_id: UUID,
                                  user_id: UUID, good_qty: int | None = None,
                                  warehouse_code: str = "FG"):
        """
        工單完工入庫：成品進 FG 倉，工單狀態轉 completed。

        good_qty 未指定時，取「最後一道工序」的良品數作為入庫數——
        前段工序的產出是半成品，若把每道工序的 good_qty 加總會嚴重灌水。
        """
        wo = (await db.execute(
            select(WorkOrder).where(WorkOrder.id == wo_id, WorkOrder.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if not wo:
            return None
        if wo.status == "completed":
            raise ValueError(f"工單 {wo.wo_number} 已完工入庫，不可重複入庫")
        if wo.status not in ("in_progress", "released"):
            raise ValueError(f"工單狀態為 {wo.status}，無法完工入庫")

        ops = (await db.execute(
            select(WoOperation).where(WoOperation.wo_id == wo_id).order_by(WoOperation.op_seq)
        )).scalars().all()
        unfinished = [o.op_name for o in ops if o.status != "completed"]
        if unfinished:
            raise ValueError(f"尚有工序未完成：{'、'.join(unfinished)}")

        if good_qty is None:
            good_qty = ops[-1].good_qty if ops else wo.quantity
        if good_qty <= 0:
            raise ValueError("入庫數量必須大於0")

        balance = (await db.execute(
            select(InventoryBalance).where(
                InventoryBalance.tenant_id == tenant_id,
                InventoryBalance.product_id == wo.product_id,
                InventoryBalance.warehouse_code == warehouse_code,
            )
        )).scalar_one_or_none()
        now = datetime.utcnow()
        if balance:
            balance.qty_on_hand = Decimal(balance.qty_on_hand) + Decimal(good_qty)
            balance.last_updated = now
        else:
            balance = InventoryBalance(
                tenant_id=tenant_id,
                product_id=wo.product_id,
                warehouse_code=warehouse_code,
                qty_on_hand=Decimal(good_qty),
            )
            db.add(balance)

        db.add(InventoryTransaction(
            tenant_id=tenant_id,
            transaction_type="RECEIPT",
            product_id=wo.product_id,
            warehouse_code=warehouse_code,
            qty=Decimal(good_qty),
            source_type="WO",
            source_id=wo_id,
            notes=f"工單 {wo.wo_number} 完工入庫",
            created_by=user_id,
        ))

        wo.completed_qty = (wo.completed_qty or 0) + good_qty
        wo.status = "completed"
        wo.actual_end = now
        await db.flush()

        return {
            "wo_number": wo.wo_number,
            "product_id": str(wo.product_id),
            "received_qty": good_qty,
            "planned_qty": wo.quantity,
            "warehouse_code": warehouse_code,
            "fg_balance_after": float(balance.qty_on_hand),
        }
