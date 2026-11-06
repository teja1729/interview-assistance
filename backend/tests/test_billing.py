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
from app.services.usage import effective_plan

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


@pytest.mark.parametrize(
    ("plan", "amount"),
    [("starter", 99900), ("pro", 299900), ("senior", 499900)],
)
def test_razorpay_create_order_uses_server_price(account, engine, monkeypatch, plan, amount):
    settings = replace(
        billing.settings,
        razorpay_key_id="rzp_test_fixture",
        razorpay_key_secret="secret_fixture",
        razorpay_starter_monthly_amount_paise=99900,
        razorpay_pro_monthly_amount_paise=299900,
        razorpay_senior_monthly_amount_paise=499900,
    )
    monkeypatch.setattr(billing, "settings", settings)
    monkeypatch.setattr(billing.razorpay, "settings", settings)
    calls = []

    def create_order(amount, receipt, workspace_id, plan, billing_period):
        calls.append((amount, receipt, workspace_id, plan, billing_period))
        return {"id": "order_test_1", "amount": amount, "currency": "INR"}

    monkeypatch.setattr(billing.razorpay, "create_order", create_order)
    result = account.post("/api/billing/create-order", json={"plan": plan, "period": "monthly", "amount": 1})

    assert result.status_code == 200
    assert result.json()["order_id"] == "order_test_1"
    assert result.json()["amount"] == amount
    assert len(calls) == 1
    assert calls[0][0] == amount
    assert calls[0][1].startswith(f"{plan[:6]}-")
    assert calls[0][2:] == (account.workspace_id, plan, "monthly")
    with Session(engine) as session:
        workspace = session.get(Workspace, account.workspace_id)
        assert workspace.razorpay_order_id == "order_test_1"
        assert workspace.razorpay_order_amount_paise == amount
        assert workspace.razorpay_order_plan == plan


@pytest.mark.parametrize(
    ("plan", "amount"),
    [("starter", 99900), ("pro", 299900), ("senior", 499900)],
)
def test_razorpay_payment_verification_grants_term_once(account, engine, monkeypatch, plan, amount):
    settings = replace(
        billing.settings,
        razorpay_key_id="rzp_test_fixture",
        razorpay_key_secret="secret_fixture",
    )
    monkeypatch.setattr(billing, "settings", settings)
    monkeypatch.setattr(billing.razorpay, "settings", settings)
    with Session(engine) as session:
        workspace = session.get(Workspace, account.workspace_id)
        workspace.razorpay_order_id = f"order_{plan}_test"
        workspace.razorpay_order_amount_paise = amount
        workspace.razorpay_order_plan = plan
        workspace.razorpay_order_period = "monthly"
        session.add(workspace)
        session.commit()

    monkeypatch.setattr(billing.razorpay, "verify_order_payment_signature", lambda *args: True)
    monkeypatch.setattr(
        billing.razorpay,
        "fetch_payment",
        lambda payment_id: {
            "id": payment_id,
            "order_id": f"order_{plan}_test",
            "amount": amount,
            "currency": "INR",
            "status": "captured",
        },
    )
    payload = {
        "razorpay_payment_id": "pay_test_2",
        "razorpay_order_id": f"order_{plan}_test",
        "razorpay_signature": "signed_fixture",
    }
    first = account.post("/api/billing/verify-payment", json=payload)
    assert first.status_code == 200
    expiry = first.json()["expires_at"]
    repeated = account.post("/api/billing/verify-payment", json=payload)
    assert repeated.status_code == 200
    assert repeated.json()["expires_at"] == expiry
    with Session(engine) as session:
        workspace = session.get(Workspace, account.workspace_id)
        assert workspace.plan == plan
        assert workspace.billing_provider == "razorpay_order"
        assert workspace.razorpay_payment_id == "pay_test_2"
        assert workspace.billing_expires_at == expiry


def test_razorpay_invalid_signature_does_not_grant_plan(account, engine, monkeypatch):
    settings = replace(billing.settings, razorpay_key_secret="secret_fixture")
    monkeypatch.setattr(billing, "settings", settings)
    monkeypatch.setattr(billing.razorpay, "settings", settings)
    with Session(engine) as session:
        workspace = session.get(Workspace, account.workspace_id)
        workspace.razorpay_order_id = "order_test_3"
        workspace.razorpay_order_amount_paise = 299900
        workspace.razorpay_order_plan = "pro"
        workspace.razorpay_order_period = "monthly"
        session.add(workspace)
        session.commit()

    monkeypatch.setattr(billing.razorpay, "verify_order_payment_signature", lambda *args: False)
    result = account.post(
        "/api/billing/verify-payment",
        json={
            "razorpay_payment_id": "pay_bad",
            "razorpay_order_id": "order_test_3",
            "razorpay_signature": "wrong",
        },
    )
    assert result.status_code == 400
    with Session(engine) as session:
        workspace = session.get(Workspace, account.workspace_id)
        assert workspace.plan == "free"
        assert workspace.razorpay_payment_id is None


def test_razorpay_verification_requires_all_fields(account):
    result = account.post("/api/billing/verify-payment", json={"razorpay_order_id": "order_missing"})
    assert result.status_code == 400


def test_expired_one_time_pro_access_uses_starter_limits():
    workspace = Workspace(name="Expired account", plan="pro", billing_expires_at=time.time() - 1)
    assert effective_plan(workspace) == "free"
