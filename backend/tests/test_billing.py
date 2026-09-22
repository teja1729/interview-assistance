"""Real webhook signatures, idempotency and concurrent subscription reconciliation."""

import hashlib
import hmac
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
import stripe
from sqlmodel import Session, select

from app.api import billing
from app.models import BillingEvent, Workspace
from app.services import billing as service

SECRET = "whsec_test_fixture"


def subscription(plan="pro", status="active", created=1):
    return stripe.StripeObject.construct_from(
        {
            "id": f"sub_{plan}_{created}",
            "customer": "cus_test",
            "status": status,
            "created": created,
            "items": {"data": [{"price": {"id": f"price_{plan}_test"}}]},
        },
        "test",
    )


def response(*subscriptions):
    return stripe.StripeObject.construct_from({"data": list(subscriptions), "has_more": False}, "test")


def send(client, event_id="evt_test", event_type="customer.subscription.updated", created=None, valid=True):
    payload = json.dumps(
        {
            "id": event_id,
            "type": event_type,
            "created": created or int(time.time()),
            "data": {"object": {"id": "sub_test", "customer": "cus_test"}},
        }
    )
    timestamp = int(time.time())
    signature = hmac.new(SECRET.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256).hexdigest()
    headers = {
        "stripe-signature": f"t={timestamp},v1={signature}" if valid else "wrong",
        "Content-Type": "application/json",
    }
    return client.post("/api/billing/webhook", content=payload, headers=headers)


@pytest.fixture
def account(clients, engine, monkeypatch):
    settings = replace(
        billing.settings,
        stripe_key="sk_test_fixture",
        stripe_webhook_secret=SECRET,
        stripe_pro_price="price_pro_test",
        stripe_team_price="price_team_test",
    )
    monkeypatch.setattr(billing, "settings", settings)
    monkeypatch.setattr(service, "settings", settings)
    client = clients()
    with Session(engine) as session:
        workspace = session.get(Workspace, client.workspace_id)
        workspace.stripe_customer_id = "cus_test"
        session.add(workspace)
        session.commit()
    return client


def test_signed_webhook_updates_plan_idempotently(account, engine, monkeypatch):
    monkeypatch.setattr(stripe.Subscription, "list", lambda **kwargs: response(subscription()))
    assert send(account, valid=False).status_code == 400
    assert send(account).status_code == 200
    assert send(account).status_code == 200
    with Session(engine) as session:
        workspace = session.get(Workspace, account.workspace_id)
        assert workspace.plan == "pro"
        assert workspace.billing_version == 1
        assert len(session.exec(select(BillingEvent)).all()) == 1


def test_old_subscription_event_does_not_revoke_current_plan(account, engine, monkeypatch):
    monkeypatch.setattr(
        stripe.Subscription,
        "list",
        lambda **kwargs: response(
            subscription("team", created=2),
            subscription("pro", status="canceled"),
        ),
    )
    assert send(account, "evt_current", created=200).status_code == 200
    assert send(account, "evt_delayed", "customer.subscription.deleted", created=100).status_code == 200
    with Session(engine) as session:
        workspace = session.get(Workspace, account.workspace_id)
        assert workspace.plan == "team"
        assert workspace.stripe_subscription_id == "sub_team_2"
        assert workspace.billing_event_at == 200


def test_concurrent_stale_snapshot_is_fenced_and_refetched(account, engine, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    guard = threading.Lock()
    calls = 0

    def listing(**kwargs):
        nonlocal calls
        with guard:
            calls += 1
            first = calls == 1
        if first:
            entered.set()
            assert release.wait(10)
            return response(subscription("pro"))
        return response(subscription("team", created=2))

    monkeypatch.setattr(stripe.Subscription, "list", listing)
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = executor.submit(send, account, "evt_slow")
        try:
            assert entered.wait(10)
            assert send(account, "evt_fast").status_code == 200
        finally:
            release.set()
        assert pending.result(timeout=10).status_code == 200
    with Session(engine) as session:
        workspace = session.get(Workspace, account.workspace_id)
        assert workspace.plan == "team"
        assert workspace.billing_version == 2
        assert len(session.exec(select(BillingEvent)).all()) == 2
    assert calls == 3
