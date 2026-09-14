from typing import Optional
from pydantic import BaseModel, EmailStr, Field

VALID_STATUSES = {"new", "contacted", "quoted", "won", "lost", "spam"}


class InquiryCreate(BaseModel):
    """官網訪客送出的詢價內容。所有長度上限同時是資料庫欄位上限，避免寫入時才爆錯。"""
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    company: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    product_type: Optional[str] = Field(default=None, max_length=100)
    quantity: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=4000)
    source_page: Optional[str] = Field(default=None, max_length=200)


class InquiryStatusUpdate(BaseModel):
    status: str = Field(description="new / contacted / quoted / won / lost / spam")
    internal_notes: Optional[str] = Field(default=None, max_length=4000)


class InquiryOut(BaseModel):
    id: str
    name: str
    company: Optional[str]
    email: str
    phone: Optional[str]
    product_type: Optional[str]
    quantity: Optional[str]
    description: Optional[str]
    status: str
    internal_notes: Optional[str]
    converted_customer_id: Optional[str]
    created_at: Optional[str]
