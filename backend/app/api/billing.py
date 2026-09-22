"""Stripe Checkout + portal, signed idempotent webhooks, and server-owned entitlements.

Client redirects never grant a plan. Subscription events reconcile current customer subscriptions through a versioned service.
"""

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool

from ..auth import Context, current_context
from ..config import settings
from ..db import get_session
from ..services.billing import enabled, prices, reconcile
from ..services.usage import PLANS, summary

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("")
def info(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return {
        **summary(session, ctx.workspace),
        "status": ctx.workspace.billing_status,
        "enabled": enabled(),
        "plans": [
            {"id": key, **value, "available": key == "free" or bool(prices().get(key))}
            for key, value in PLANS.items()
            if key in {"free", "pro"}
        ],
    }


class CheckoutInput(BaseModel):
    plan: str


@router.post("/checkout")
def checkout(body: CheckoutInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    ctx.require_owner()
    if body.plan != "pro":
        raise HTTPException(400, "Choose an available personal plan")
    price = prices().get(body.plan)
    if not enabled() or not price:
        raise HTTPException(503, "Billing is not configured for this plan")
    if ctx.workspace.stripe_subscription_id and ctx.workspace.billing_status in {"active", "trialing", "past_due"}:
        raise HTTPException(409, "Manage your existing subscription in the billing portal")
    if not ctx.workspace.stripe_customer_id:
        customer = stripe.Customer.create(
            api_key=settings.stripe_key,
            email=ctx.user.email,
            name=ctx.workspace.name,
            metadata={"workspace_id": ctx.workspace.id},
            idempotency_key=f"workspace-customer-{ctx.workspace.id}",
        )
        ctx.workspace.stripe_customer_id = customer.id
        session.add(ctx.workspace)
        session.commit()
    checkout_session = stripe.checkout.Session.create(
        api_key=settings.stripe_key,
        customer=ctx.workspace.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price, "quantity": 1}],
        client_reference_id=ctx.workspace.id,
        subscription_data={"metadata": {"workspace_id": ctx.workspace.id}},
        success_url=f"{settings.frontend_origin}/billing?checkout=success",
        cancel_url=f"{settings.frontend_origin}/billing?checkout=cancelled",
    )
    return {"url": checkout_session.url}


@router.post("/portal")
def portal(ctx: Context = Depends(current_context)):
    ctx.require_owner()
    if not enabled() or not ctx.workspace.stripe_customer_id:
        raise HTTPException(400, "No billing account exists yet")
    result = stripe.billing_portal.Session.create(
        api_key=settings.stripe_key,
        customer=ctx.workspace.stripe_customer_id,
        return_url=f"{settings.frontend_origin}/billing",
    )
    return {"url": result.url}


@router.post("/webhook")
async def webhook(request: Request, session: Session = Depends(get_session)):
    if not enabled():
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
