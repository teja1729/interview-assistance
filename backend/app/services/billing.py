"""Reconcile current subscriptions, fencing concurrent webhook snapshots with a DB version.

Event payloads are notifications, not entitlement snapshots. A canceled old subscription must
not revoke a newer active subscription. No write transaction spans the Stripe network request.
"""

import stripe
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from ..config import settings
from ..models import BillingEvent, Workspace

SUBSCRIPTION_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


def prices():
    return {"pro": settings.stripe_pro_price, "team": settings.stripe_team_price}


def enabled():
    return bool(settings.stripe_key and settings.stripe_webhook_secret)


def customer_snapshot(customer_id):
    subscriptions = stripe.Subscription.list(customer=customer_id, status="all", limit=100, api_key=settings.stripe_key)
    if subscriptions.has_more:
        # Never silently grant/revoke from an incomplete list. Operator review is needed here.
        raise HTTPException(503, "Billing reconciliation needs operator review")
    selected, selected_plan, rank = None, "free", -1
    for subscription in subscriptions.data:
        price_ids = {item.price.id for item in subscription["items"].data}
        plan = next((key for key in ("team", "pro") if prices()[key] and prices()[key] in price_ids), "free")
        current_rank = {"free": 0, "pro": 1, "team": 2}[plan] if subscription.status in {"active", "trialing"} else 0
        if current_rank > rank or (
            current_rank == rank and getattr(subscription, "created", 0) > getattr(selected, "created", 0)
        ):
            selected, selected_plan, rank = subscription, plan if current_rank else "free", current_rank
    return {
        "plan": selected_plan,
        "billing_status": selected.status if selected else "free",
        "stripe_subscription_id": selected.id if selected else None,
    }


def reconcile(session, event):
    for _ in range(3):
        if session.get(BillingEvent, event.id):
            return
        if event.type in SUBSCRIPTION_EVENTS:
            customer_id = getattr(event.data.object, "customer", None)
            workspace = (
                session.exec(select(Workspace).where(Workspace.stripe_customer_id == customer_id)).first()
                if customer_id
                else None
            )
            if workspace:
                workspace_id, version = workspace.id, workspace.billing_version
                event_at = max(workspace.billing_event_at, event.created)
                session.rollback()
                snapshot = customer_snapshot(customer_id)
                result = session.execute(
                    update(Workspace)
                    .where(Workspace.id == workspace_id, Workspace.billing_version == version)
                    .values(**snapshot, billing_version=version + 1, billing_event_at=event_at)
                    .execution_options(synchronize_session=False)
                )
                if result.rowcount != 1:
                    session.rollback()
                    continue  # Another snapshot committed: fetch Stripe again before retrying.
        session.add(BillingEvent(id=event.id))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            if not session.get(BillingEvent, event.id):
                raise
        return
    raise HTTPException(409, "Billing changed concurrently. Retry this event.")
