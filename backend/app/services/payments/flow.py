# app/services/payments/flow.py
"""
Flow.cl provider implementation.

*** UNVERIFIED AGAINST A LIVE SANDBOX. *** The spec's own "Known risks" section says exactly
this: "The implementation follows Flow's documented REST conventions, but the current spec was
not confirmed. Run create, confirm and refund in sandbox before production." No sandbox account
exists as of writing. Endpoint paths, exact parameter names, and the webhook signing scheme below
are built from Flow's publicly documented conventions and must be confirmed against a real
sandbox account before this ever touches production traffic -- every method below has a
# TODO(flow-sandbox-verify) marking the specific thing to confirm.

CLP has no minor unit. Every amount here is passed to Flow as a whole-peso Decimal -- NEVER
multiplied by 100. That *100 mistake is explicitly called out in the spec as a Stripe-habit bug
that would overcharge by 100x.
"""
import hashlib
import hmac
import os
from decimal import Decimal
from typing import Optional

import requests

from app.services.payments.base import (
    PaymentProvider,
    ProviderPaymentResult,
    ProviderRefundResult,
    ProviderStatus,
)

SANDBOX_BASE_URL = "https://sandbox.flow.cl/api"
PRODUCTION_BASE_URL = "https://www.flow.cl/api"

# Flow's documented numeric status codes (payment/getStatus response `status` field).
# TODO(flow-sandbox-verify): confirm these values against a real sandbox response.
_STATUS_MAP = {
    1: "pending",   # pending
    2: "succeeded", # paid
    3: "failed",    # rejected
    4: "failed",    # canceled
}


class FlowProvider(PaymentProvider):
    def __init__(self, credentials: dict, *, is_sandbox: bool):
        super().__init__(credentials, is_sandbox=is_sandbox)
        self.api_key = credentials.get("api_key", "")
        self.secret_key = credentials.get("secret_key", "")
        self.base_url = SANDBOX_BASE_URL if is_sandbox else PRODUCTION_BASE_URL

    def _sign(self, params: dict) -> str:
        """Flow's documented request-signing scheme: concatenate "key"+"value" for every
        param, sorted alphabetically by key, then HMAC-SHA256 with the merchant's secret_key.
        TODO(flow-sandbox-verify): confirm the exact concatenation format against sandbox --
        Flow's docs are not perfectly precise on separator/encoding details."""
        ordered = sorted(params.items(), key=lambda kv: kv[0])
        to_sign = "".join(f"{k}{v}" for k, v in ordered)
        return hmac.new(self.secret_key.encode(), to_sign.encode(), hashlib.sha256).hexdigest()

    def create_payment(
        self, *, booking_id: str, amount: Decimal, currency: str, return_url: str, confirmation_url: str
    ) -> ProviderPaymentResult:
        # TODO(flow-sandbox-verify): confirm required vs optional params and exact field names.
        params = {
            "apiKey": self.api_key,
            "commerceOrder": str(booking_id),
            "subject": f"Outdaxius booking {booking_id}",
            "currency": currency,
            "amount": str(int(amount)),  # whole units -- CLP has no minor unit, never *100
            "urlConfirmation": confirmation_url,
            "urlReturn": return_url,
        }
        params["s"] = self._sign(params)

        resp = requests.post(f"{self.base_url}/payment/create", data=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        return ProviderPaymentResult(
            provider_ref=data["token"],
            redirect_url=f"{data['url']}?token={data['token']}",
        )

    def get_status(self, provider_ref: str) -> ProviderStatus:
        params = {"apiKey": self.api_key, "token": provider_ref}
        params["s"] = self._sign(params)

        resp = requests.get(f"{self.base_url}/payment/getStatus", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # TODO(flow-sandbox-verify): confirm the response shape and the `status` field name/values.
        normalized = _STATUS_MAP.get(data.get("status"), "pending")
        return ProviderStatus(provider_ref=provider_ref, status=normalized, raw=data)

    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        """Flow POSTs form-encoded data to urlConfirmation. TODO(flow-sandbox-verify): confirm
        whether Flow actually includes a signed `s` param on the confirmation callback itself, or
        whether the intended pattern is simply "trust nothing from the callback body, always call
        get_status independently" -- Flow's docs describe `s` for requests YOU send TO Flow, not
        unambiguously for the callback Flow sends to you. Until confirmed, this recomputes the
        signature the same way and rejects if it's absent or doesn't match, which is the more
        conservative failure mode (reject unsigned/garbage callbacks rather than trust them)."""
        from urllib.parse import parse_qsl

        fields = dict(parse_qsl(payload.decode("utf-8")))
        received_sig = fields.pop("s", None)
        if not received_sig:
            return False
        expected_sig = self._sign(fields)
        return hmac.compare_digest(received_sig, expected_sig)

    def refund(self, provider_ref: str, amount: Decimal) -> ProviderRefundResult:
        # TODO(flow-sandbox-verify): confirm the refund endpoint path and required params --
        # Flow's refund/create may expect flowOrder rather than the payment token.
        params = {
            "apiKey": self.api_key,
            "token": provider_ref,
            "amount": str(int(amount)),
        }
        params["s"] = self._sign(params)

        try:
            resp = requests.post(f"{self.base_url}/refund/create", data=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            return ProviderRefundResult(success=False, failure_reason=str(exc))

        return ProviderRefundResult(success=True, provider_refund_ref=data.get("token"))
