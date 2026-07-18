# app/models/company_payment_account.py
import uuid
from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime, LargeBinary, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class CompanyPaymentAccount(Base):
    """
    Each company is its own merchant of record; the platform never holds funds. credentials_encrypted
    is Fernet ciphertext (Phase 4) and must NEVER be returned by any endpoint or Pydantic schema.
    charges_enabled gates whether the company may publish a sellable schedule.
    """
    __tablename__ = "company_payment_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)
    external_account_id = Column(String, nullable=True)
    credentials_encrypted = Column(LargeBinary, nullable=False)
    charges_enabled = Column(Boolean, nullable=False, default=False)
    currency = Column(String(3), nullable=False, default="CLP")
    is_sandbox = Column(Boolean, nullable=False, default=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "provider IN ('flow', 'stripe', 'transbank', 'mercadopago')",
            name="ck_payment_accounts_provider",
        ),
        UniqueConstraint("company_id", "provider", name="uq_payment_account_provider"),
    )
