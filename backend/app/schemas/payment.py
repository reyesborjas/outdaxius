# app/schemas/payment.py
from pydantic import BaseModel, AnyUrl, Field
from typing import Optional, Literal
from decimal import Decimal
import uuid

class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = "USD"
    voucher_url: Optional[AnyUrl] = None
    reference: Optional[str] = None

class PaymentOut(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: Decimal
    currency: str
    status: Literal["pending", "succeeded", "failed", "refunded", "partially_refunded"]
    provider: Optional[str] = None
    voucher_url: Optional[str] = None
    reference: Optional[str] = None
    class Config:
        from_attributes = True
