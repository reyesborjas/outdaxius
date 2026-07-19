# app/api/company_payments.py
"""
Company payment account onboarding. Credentials are encrypted on write (app.core.crypto) and
NEVER returned by any endpoint here -- CompanyPaymentAccountOut has no credential field at all,
not merely one excluded from serialization, so there is no code path that can leak it.
"""
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.core.permissions import check_company_admin
from app.core.crypto import encrypt_credentials
from app.models.user import User
from app.models.company import Company
from app.models.company_payment_account import CompanyPaymentAccount

router = APIRouter(prefix="/companies", tags=["company-payments"])


class CompanyPaymentAccountCreate(BaseModel):
    provider: Literal["flow", "stripe", "transbank", "mercadopago"]
    is_sandbox: bool = True
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    external_account_id: Optional[str] = None
    # Provider-specific raw credentials (e.g. {"api_key": ..., "secret_key": ...} for Flow).
    # Encrypted immediately on write; never stored or logged in plaintext beyond this request.
    credentials: Dict[str, str]


class CompanyPaymentAccountOut(BaseModel):
    id: UUID
    company_id: UUID
    provider: str
    external_account_id: Optional[str] = None
    charges_enabled: bool
    currency: str
    is_sandbox: bool
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/{company_id}/payment-accounts",
    response_model=CompanyPaymentAccountOut,
    status_code=status.HTTP_201_CREATED,
)
def create_or_update_payment_account(
    company_id: UUID,
    payload: CompanyPaymentAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_company_admin(db, current_user, company_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Company admin access required")

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, detail="Company not found")

    encrypted = encrypt_credentials(payload.credentials)

    # uq_payment_account_provider: one account per (company, provider) -- update in place if the
    # company is re-submitting credentials for a provider it already onboarded.
    account = db.query(CompanyPaymentAccount).filter(
        CompanyPaymentAccount.company_id == company_id,
        CompanyPaymentAccount.provider == payload.provider,
    ).first()

    if account:
        account.credentials_encrypted = encrypted
        account.external_account_id = payload.external_account_id
        account.currency = payload.currency
        account.is_sandbox = payload.is_sandbox
        # Re-submitting credentials invalidates any prior verification.
        account.charges_enabled = False
        account.verified_at = None
    else:
        account = CompanyPaymentAccount(
            company_id=company_id,
            provider=payload.provider,
            external_account_id=payload.external_account_id,
            credentials_encrypted=encrypted,
            currency=payload.currency,
            is_sandbox=payload.is_sandbox,
            charges_enabled=False,
        )
        db.add(account)

    db.commit()
    db.refresh(account)
    return account


@router.get("/{company_id}/payment-accounts", response_model=List[CompanyPaymentAccountOut])
def list_payment_accounts(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_company_admin(db, current_user, company_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Company admin access required")

    return db.query(CompanyPaymentAccount).filter(
        CompanyPaymentAccount.company_id == company_id
    ).all()


@router.post(
    "/{company_id}/payment-accounts/{account_id}/verify",
    response_model=CompanyPaymentAccountOut,
)
def verify_payment_account(
    company_id: UUID,
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SCAFFOLD: there is no live Flow/Stripe/... sandbox to actually call. For a sandbox account
    this simulates a successful provider verification (sets charges_enabled=True) so the rest of
    the system -- the publication gate, the onboarding screen -- can be exercised end-to-end
    without a real gateway. Replace the body of this function with a real provider.get_status-style
    verification call once sandbox credentials exist; production accounts (is_sandbox=False)
    deliberately refuse to auto-verify here.
    """
    if not check_company_admin(db, current_user, company_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Company admin access required")

    account = db.query(CompanyPaymentAccount).filter(
        CompanyPaymentAccount.id == account_id,
        CompanyPaymentAccount.company_id == company_id,
    ).first()
    if not account:
        raise HTTPException(404, detail="Payment account not found")

    if not account.is_sandbox:
        raise HTTPException(
            400,
            detail="Production accounts require a real provider verification call, not yet "
                   "implemented (no live gateway to verify against)."
        )

    account.charges_enabled = True
    account.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(account)
    return account
