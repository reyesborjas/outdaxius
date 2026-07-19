# app/services/payments/base.py
"""
Provider abstraction. Each company is its own merchant of record (see the spec's decision log) --
a PaymentProvider instance is always constructed from ONE company's decrypted credentials, never
shared across companies, and the platform itself never touches the money.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class ProviderPaymentResult:
    provider_ref: str
    redirect_url: str


@dataclass
class ProviderStatus:
    provider_ref: str
    status: str  # normalized to one of: pending | succeeded | failed
    raw: dict


@dataclass
class ProviderRefundResult:
    success: bool
    provider_refund_ref: Optional[str] = None
    failure_reason: Optional[str] = None


class PaymentProvider(ABC):
    """One instance per (company, provider) pair, built from that company's own decrypted
    credentials. Amounts are always Decimal in the CURRENCY THE PROVIDER ACTUALLY CHARGES IN --
    callers must not assume cents/minor units; see FlowProvider's docstring for why."""

    def __init__(self, credentials: dict, *, is_sandbox: bool):
        self.credentials = credentials
        self.is_sandbox = is_sandbox

    @abstractmethod
    def create_payment(
        self, *, booking_id: str, amount: Decimal, currency: str, return_url: str, confirmation_url: str
    ) -> ProviderPaymentResult:
        """Start a payment; returns a redirect_url for the client and a provider_ref to store on
        the Payment row and use for all subsequent lookups."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self, provider_ref: str) -> ProviderStatus:
        """The ONLY authoritative source of payment status. Webhook handlers must call this
        rather than trusting the callback payload -- see payments_flow.py's webhook handler."""
        raise NotImplementedError

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        raise NotImplementedError

    @abstractmethod
    def refund(self, provider_ref: str, amount: Decimal) -> ProviderRefundResult:
        raise NotImplementedError


def get_provider(company_payment_account) -> PaymentProvider:
    """Factory: decrypts the account's credentials and constructs the right provider instance.
    Import is local to avoid a base.py <-> flow.py import cycle at module load time."""
    from app.core.crypto import decrypt_credentials
    from app.services.payments.flow import FlowProvider

    credentials = decrypt_credentials(company_payment_account.credentials_encrypted)

    if company_payment_account.provider == "flow":
        return FlowProvider(credentials, is_sandbox=company_payment_account.is_sandbox)

    raise NotImplementedError(
        f"No provider implementation for '{company_payment_account.provider}' yet -- "
        "only 'flow' is implemented. Stripe/Transbank/Mercadopago are declared in the "
        "company_payment_accounts CHECK constraint for future providers, not implemented here."
    )
