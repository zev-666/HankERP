from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.customer import Customer, Contact, CrmActivity
from app.modules.customers.schemas import CustomerCreate, CustomerUpdate, ActivityCreate


class CustomerService:
    """客戶管理CRM業務邏輯層 — 與 inventory/production service 保持一致架構"""

    async def _next_code(self, db: AsyncSession) -> str:
        count = (await db.execute(select(func.count(Customer.id)))).scalar() or 0
        return f"C{count+1:04d}"

    async def list_customers(self, db: AsyncSession, tenant_id: UUID,
                              search: Optional[str] = None,
                              industry: Optional[str] = None,
                              tier: Optional[str] = None,
                              skip: int = 0, limit: int = 50):
        q = select(Customer).where(Customer.tenant_id == tenant_id)
        if search:
            q = q.where(Customer.name.ilike(f"%{search}%"))
        if industry:
            q = q.where(Customer.industry == industry)
        if tier:
            q = q.where(Customer.tier == tier)
        q = q.offset(skip).limit(limit)
        result = await db.execute(q)
        return result.scalars().all()

    async def create_customer(self, db: AsyncSession, tenant_id: UUID,
                               user_id: UUID, data: CustomerCreate) -> Customer:
        code = await self._next_code(db)
        c = Customer(
            tenant_id=tenant_id,
            code=code,
            name=data.name,
            company_type=data.company_type,
            industry=data.industry,
            tax_id=data.tax_id,
            contact_name=data.contact_name,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            billing_address=data.billing_address,
            credit_limit=data.credit_limit,
            payment_terms=data.payment_terms,
            tier=data.tier,
            notes=data.notes,
            created_by=user_id,
        )
        db.add(c)
        await db.flush()
        for ct in data.contacts:
            db.add(Contact(customer_id=c.id, **ct.model_dump()))
        await db.flush()
        return c

    async def get_customer(self, db: AsyncSession, tenant_id: UUID,
                           customer_id: UUID) -> Optional[Customer]:
        q = select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
        result = await db.execute(q)
        return result.scalar_one_or_none()

    async def update_customer(self, db: AsyncSession, tenant_id: UUID,
                               customer_id: UUID, data: CustomerUpdate) -> Optional[Customer]:
        c = await self.get_customer(db, tenant_id, customer_id)
        if not c:
            return None
        for field, val in data.model_dump(exclude_none=True).items():
            setattr(c, field, val)
        await db.flush()
        return c

    async def list_activities(self, db: AsyncSession, customer_id: UUID):
        q = select(CrmActivity).where(
            CrmActivity.customer_id == customer_id
        ).order_by(CrmActivity.created_at.desc())
        result = await db.execute(q)
        return result.scalars().all()

    async def add_activity(self, db: AsyncSession, customer_id: UUID,
                           user_id: UUID, data: ActivityCreate) -> CrmActivity:
        act = CrmActivity(
            customer_id=customer_id,
            activity_type=data.activity_type,
            subject=data.subject,
            content=data.content,
            outcome=data.outcome,
            next_action=data.next_action,
            next_action_date=data.next_action_date,
            created_by=user_id,
        )
        db.add(act)
        await db.flush()
        return act

    async def get_customer_360(self, db: AsyncSession, tenant_id: UUID, customer_id: UUID) -> Optional[dict]:
        """客戶360視圖：基本資料 + 互動記錄 + 報價歷史（供未來客戶詳情頁使用）"""
        c = await self.get_customer(db, tenant_id, customer_id)
        if not c:
            return None
        activities = await self.list_activities(db, customer_id)

        from app.models.quotation import Quotation
        q = select(Quotation).where(Quotation.customer_id == customer_id).order_by(Quotation.created_at.desc())
        quotes = (await db.execute(q)).scalars().all()

        return {
            "customer": c,
            "activities": activities,
            "quotations": quotes,
            "total_quotes": len(quotes),
            "won_quotes": len([q for q in quotes if q.status == "accepted"]),
        }
