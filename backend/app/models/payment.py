# app/models/payment.py
import uuid
from sqlalchemy import Column, ForeignKey, String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class Payment(Base):
    __tablename__ = "payments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"))
    method_id  = Column(UUID(as_uuid=True), nullable=True)  # opcional en MVP
    amount   = Column(Numeric(12,2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status   = Column(String, nullable=False, default="pending")  # payment_status enum: pending|succeeded|failed|refunded|partially_refunded
    provider = Column(String, nullable=True)      # e.g. "flow" -- null for the manual voucher-upload path
    provider_ref = Column(String, nullable=True)  # provider's own payment/token id, for idempotent webhook lookups
    voucher_url = Column(String, nullable=True)
    reference   = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
