from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr

class ContactCreate(BaseModel):
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_primary: bool = False

class ContactOut(ContactCreate):
    id: UUID
    class Config: from_attributes = True

class CustomerCreate(BaseModel):
    name: str
    company_type: Optional[str] = None   # 品牌商/代理商/零售商
    industry: Optional[str] = None       # 彩妝/家電/酒類/嬰兒用品
    tax_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    billing_address: Optional[str] = None
    credit_limit: Decimal = Decimal("0")
    payment_terms: int = 30
    tier: str = "standard"
    notes: Optional[str] = None
    contacts: List[ContactCreate] = []

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    tier: Optional[str] = None
    notes: Optional[str] = None

class CustomerOut(BaseModel):
    id: UUID
    code: Optional[str]
    name: str
    company_type: Optional[str]
    industry: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    tier: str
    payment_terms: int
    created_at: datetime
    class Config: from_attributes = True

class ActivityCreate(BaseModel):
    activity_type: str   # call/email/visit/sample_sent
    subject: str
    content: Optional[str] = None
    outcome: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None
