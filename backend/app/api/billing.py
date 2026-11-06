"""Razorpay Standard Checkout, Stripe legacy billing, and server-owned entitlements.

The client cannot choose the price. Razorpay signatures and fetched payment state are checked before access is granted.
"""

import time
import uuid

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import update
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool

from ..auth import Context, current_context
from ..config import settings
from ..db import get_session
from ..models import Workspace
from ..providers import razorpay
from ..services.billing import enabled, reconcile
from ..services.usage import PLANS, summary

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("")
def info(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return {
        **summary(session, ctx.workspace),
        "status": ctx.workspace.billing_status,
        "provider": ctx.workspace.billing_provider or ("stripe" if ctx.workspace.stripe_customer_id else ""),
        "expires_at": ctx.workspace.billing_expires_at,
        "effective_status": (
            "expired"
            if ctx.workspace.billing_expires_at and ctx.workspace.billing_expires_at <= time.time()
            else ctx.workspace.billing_status
        ),
        "enabled": enabled(),
        "checkout_prices_paise": {
            "starter": {
                "monthly": settings.razorpay_starter_monthly_amount_paise,
                "yearly": settings.razorpay_starter_yearly_amount_paise,
            },
            "pro": {
                "monthly": settings.razorpay_pro_monthly_amount_paise,
                "yearly": settings.razorpay_pro_yearly_amount_paise,
            },
            "senior": {
                "monthly": settings.razorpay_senior_monthly_amount_paise,
                "yearly": settings.razorpay_senior_yearly_amount_paise,
            },
        },
        "plans": [
            {
                "id": key,
                **value,
                "available": key == "free"
                or (
                    key in {"starter", "pro", "senior"}
                    and bool(settings.razorpay_key_id and settings.razorpay_key_secret)
                ),
                "periods_available": ["monthly", "yearly"]
                if key in {"starter", "pro", "senior"} and settings.razorpay_key_id and settings.razorpay_key_secret
                else [],
            }
            for key, value in PLANS.items()
            if key in {"free", "starter", "pro", "senior"}
        ],
    }


@router.post("/portal")
def portal(ctx: Context = Depends(current_context)):
    ctx.require_owner()
    if not (settings.stripe_key and settings.stripe_webhook_secret) or not ctx.workspace.stripe_customer_id:
        raise HTTPException(400, "No billing account exists yet")
    result = stripe.billing_portal.Session.create(
        api_key=settings.stripe_key,
        customer=ctx.workspace.stripe_customer_id,
        return_url=f"{settings.frontend_origin}/billing",
    )
    return {"url": result.url}


class OrderInput(BaseModel):
    plan: str
    period: str


@router.post("/create-order")
async def create_order(
    body: OrderInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    ctx.require_owner()
    if body.plan not in {"starter", "pro", "senior"}:
        raise HTTPException(400, "Choose an available paid plan")
    if body.period not in {"monthly", "yearly"}:
        raise HTTPException(400, "Choose a valid billing period")
    if not (settings.razorpay_key_id and settings.razorpay_key_secret):
        raise HTTPException(503, "Razorpay Standard Checkout is not configured")
    if (
        ctx.workspace.billing_provider == "stripe"
        and ctx.workspace.stripe_subscription_id
        and ctx.workspace.billing_status in {"active", "trialing", "past_due"}
    ):
        raise HTTPException(409, "Manage your existing Stripe subscription before buying a plan")
    amount_config = {
        "starter": {
            "monthly": settings.razorpay_starter_monthly_amount_paise,
            "yearly": settings.razorpay_starter_yearly_amount_paise,
        },
        "pro": {
            "monthly": settings.razorpay_pro_monthly_amount_paise,
            "yearly": settings.razorpay_pro_yearly_amount_paise,
        },
        "senior": {
            "monthly": settings.razorpay_senior_monthly_amount_paise,
            "yearly": settings.razorpay_senior_yearly_amount_paise,
        },
    }
    amount = amount_config[body.plan][body.period]
    if amount < 100:
        raise HTTPException(503, "Configured plan price must be at least ₹1")
    receipt = f"{body.plan[:6]}-{uuid.uuid4().hex}"
    order = await run_in_threadpool(razorpay.create_order, amount, receipt, ctx.workspace.id, body.plan, body.period)
    if order.get("amount") != amount or order.get("currency") != "INR" or not order.get("id"):
        raise HTTPException(502, "Payment provider returned an invalid order")
    ctx.workspace.razorpay_order_id = order["id"]
    ctx.workspace.razorpay_order_amount_paise = amount
    ctx.workspace.razorpay_order_plan = body.plan
    ctx.workspace.razorpay_order_period = body.period
    ctx.workspace.billing_provider = "razorpay_order"
    session.add(ctx.workspace)
    session.commit()
    return {
        "provider": "razorpay",
        "key_id": settings.razorpay_key_id,
        "plan": body.plan,
        "order_id": order["id"],
        "amount": amount,
        "currency": "INR",
        "name": f"Suri {PLANS[body.plan]['name']}",
        "description": f"{PLANS[body.plan]['name']} plan · one-time {body.period} access",
        "prefill": {"email": ctx.user.email, "name": ctx.user.name},
    }


class PaymentVerification(BaseModel):
    razorpay_payment_id: str | None = None
    razorpay_order_id: str | None = None
    razorpay_signature: str | None = None


@router.post("/verify-payment")
async def verify_payment(
    body: PaymentVerification,
    ctx: Context = Depends(current_context),
    session: Session = Depends(get_session),
):
    ctx.require_owner()
    payment_id = body.razorpay_payment_id
    order_id = body.razorpay_order_id
    signature = body.razorpay_signature
    if not payment_id or not order_id or not signature:
        raise HTTPException(400, "Payment ID, order ID and signature are required")
    workspace = ctx.workspace
    if not settings.razorpay_key_secret or workspace.razorpay_order_id != order_id:
        raise HTTPException(400, "Payment does not match this account's current order")
    if not razorpay.verify_order_payment_signature(order_id, payment_id, signature):
        raise HTTPException(400, "Payment signature is invalid")
    payment = await run_in_threadpool(razorpay.fetch_payment, payment_id)
    if (
        payment.get("order_id") != order_id
        or payment.get("amount") != workspace.razorpay_order_amount_paise
        or payment.get("currency") != "INR"
    ):
        raise HTTPException(400, "Payment details do not match the order")
    if payment.get("status") != "captured":
        raise HTTPException(409, "Payment is not captured yet")
    if workspace.razorpay_payment_id == payment_id:
        return {"verified": True, "status": "active", "expires_at": workspace.billing_expires_at}

    now = time.time()
    if workspace.razorpay_order_plan not in {"starter", "pro", "senior"}:
        raise HTTPException(400, "Order has no valid plan")
    if workspace.razorpay_order_period not in {"monthly", "yearly"}:
        raise HTTPException(400, "Order has no valid billing period")
    duration_days = 30 if workspace.razorpay_order_period == "monthly" else 365
    start_at = max(now, workspace.billing_expires_at or 0)
    expires_at = start_at + duration_days * 24 * 60 * 60
    version = workspace.billing_version
    result = session.execute(
        update(Workspace)
        .where(
            Workspace.id == workspace.id,
            Workspace.billing_version == version,
            Workspace.razorpay_order_id == order_id,
        )
        .values(
            plan=workspace.razorpay_order_plan,
            billing_status="active",
            billing_provider="razorpay_order",
            billing_expires_at=expires_at,
            billing_event_at=int(now),
            billing_version=version + 1,
            razorpay_payment_id=payment_id,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        session.rollback()
        refreshed = session.get(Workspace, workspace.id)
        if refreshed and refreshed.razorpay_order_id == order_id and refreshed.razorpay_payment_id == payment_id:
            return {"verified": True, "status": "active", "expires_at": refreshed.billing_expires_at}
        raise HTTPException(409, "Billing changed during verification. Retry the payment check.")
    session.commit()
    return {"verified": True, "status": "active", "expires_at": expires_at}


@router.post("/webhook")
async def webhook(request: Request, session: Session = Depends(get_session)):
    if not (settings.stripe_key and settings.stripe_webhook_secret):
        raise HTTPException(503, "Billing is not configured")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, request.headers.get("stripe-signature", ""), settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(400, "Invalid webhook signature") from exc
    await run_in_threadpool(reconcile, session, event)
    return {"received": True}
