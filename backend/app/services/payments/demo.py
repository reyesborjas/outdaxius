# app/services/payments/demo.py
"""
Self-contained demo/pitch payment provider. Simulates the full pay -> confirm -> refund cycle
with zero external network calls and zero real signup, so a company can be demoed to a
prospective client (guide/agency) without a real Flow/Stripe/etc account. Never touches real
money -- exists purely to exercise the same booking/payment/cancellation code paths a real
provider would, so the demo tells the truth about how the platform actually behaves.
"""
import uuid
from decimal import Decimal

from app.services.payments.base import (
    PaymentProvider,
    ProviderPaymentResult,
    ProviderRefundResult,
    ProviderStatus,
)


class DemoProvider(PaymentProvider):
    def create_payment(
        self, *, booking_id: str, amount: Decimal, currency: str, return_url: str, confirmation_url: str
    ) -> ProviderPaymentResult:
        ref = str(uuid.uuid4())
        # A relative, in-app path rather than an external URL -- app.api.payments_flow's
        # /payments/demo/{ref} endpoints serve the simulated checkout, no external site involved.
        return ProviderPaymentResult(provider_ref=ref, redirect_url=f"/demo-checkout/{ref}")

    def get_status(self, provider_ref: str) -> ProviderStatus:
        # Demo payments are completed synchronously via POST /payments/demo/{ref}/complete --
        # nothing ever polls this for a real outcome. Implemented only to satisfy the interface.
        return ProviderStatus(provider_ref=provider_ref, status="succeeded", raw={})

    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        # No real webhook exists for the demo path -- the "complete" endpoint is a direct,
        # authenticated action by the booking's own owner, not an unauthenticated callback.
        return True

    def refund(self, provider_ref: str, amount: Decimal) -> ProviderRefundResult:
        return ProviderRefundResult(success=True, provider_refund_ref=f"demo-refund-{uuid.uuid4()}")
