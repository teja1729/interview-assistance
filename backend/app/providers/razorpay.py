"""Small server-side Razorpay REST and signature adapter."""

import hashlib
import hmac

import httpx
from fastapi import HTTPException

from ..config import settings

API_ROOT = "https://api.razorpay.com/v1"


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    try:
        response = httpx.request(
            method,
            f"{API_ROOT}/{path.lstrip('/')}",
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        # Provider error bodies can contain customer or transaction information.
        raise HTTPException(502, "Payment provider request failed") from exc
    return response.json()


def create_order(amount_paise: int, receipt: str, workspace_id: str, plan: str, billing_period: str) -> dict:
    if amount_paise < 100:
        raise HTTPException(400, "Payment amount must be at least ₹1")
    return _request(
        "POST",
        "/orders",
        {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": {"workspace_id": workspace_id, "plan": plan, "billing_period": billing_period},
        },
    )


def fetch_payment(payment_id: str) -> dict:
    return _request("GET", f"/payments/{payment_id}")


def verify_order_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    message = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(settings.razorpay_key_secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
