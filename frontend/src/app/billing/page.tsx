"use client";
import { useEffect, useState } from "react";
import { api, type Billing } from "@/lib/api";
import { Icon } from "@/components/Icon";
import { PUBLIC_PLANS } from "@/lib/plans";

type RazorpayResult = {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
};
type RazorpayCheckoutOptions = {
  key: string;
  order_id: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  prefill: { email: string; name: string };
  handler: (result: RazorpayResult) => void;
  modal: { ondismiss: () => void };
  notes?: Record<string, string>;
};
type RazorpayFailure = { error?: { description?: string } };
declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => {
      open: () => void;
      on: (
        event: "payment.failed",
        handler: (event: RazorpayFailure) => void,
      ) => void;
    };
  }
}

async function loadRazorpay(): Promise<void> {
  if (window.Razorpay) return;
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () =>
      reject(new Error("Could not load Razorpay Checkout"));
    document.body.appendChild(script);
  });
}

export default function BillingPage() {
  const [billing, setBilling] = useState<Billing | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">(
    "monthly",
  );
  useEffect(() => {
    api
      .billing()
      .then(setBilling)
      .catch((e) => setError(e.message));
  }, []);
  async function redirect(fn: () => Promise<{ url: string }>) {
    setBusy(true);
    try {
      window.location.assign((await fn()).url);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  async function startCheckout(planId: string) {
    setBusy(true);
    setError("");
    try {
      const checkout = await api.createOrder(planId, billingPeriod);
      await loadRazorpay();
      if (!window.Razorpay) throw new Error("Razorpay Checkout is unavailable");
      const modal = new window.Razorpay({
        key: checkout.key_id,
        order_id: checkout.order_id,
        amount: checkout.amount,
        currency: checkout.currency,
        name: checkout.name,
        description: checkout.description,
        prefill: checkout.prefill,
        handler: async (result) => {
          try {
            await api.verifyPayment(result);
            setNotice(
              `Payment verified. Your ${checkout.name.replace("Suri ", "")} access is active for the selected term.`,
            );
            setBilling(await api.billing());
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        },
        modal: { ondismiss: () => setBusy(false) },
      });
      modal.on("payment.failed", () => {
        setError(
          "Payment failed. Please try again or use another payment method.",
        );
        setBusy(false);
      });
      modal.open();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  async function manageSubscription() {
    await redirect(api.portal);
  }
  return (
    <div className="enter">
      <p className="eyebrow">Space for your next step</p>
      <h1 className="page-title mt-2">Plans & usage</h1>
      <p className="page-subtitle">
        Review your current usage and compare the plans shown on our homepage.
      </p>
      {error && (
        <p role="alert" className="error-banner mt-6">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="mt-6 text-sm text-accent">
          {notice}
        </p>
      )}
      {!billing ? (
        <p className="mt-8 text-sm text-muted">Loading your plan…</p>
      ) : (
        <>
          <div className="card mt-8 p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <span className="badge">Current plan</span>
                <h2 className="mt-3 text-2xl font-semibold">
                  {PUBLIC_PLANS.find((plan) => plan.id === billing.plan)
                    ?.name ?? billing.plan_name}
                </h2>
                <p className="mt-1 text-xs text-muted">
                  Usage period: {billing.period} · resets monthly in UTC
                </p>
                {billing.local_development_allowance && (
                  <p className="mt-2 text-xs text-accent">
                    Local development allowance is active.
                  </p>
                )}
                {billing.expires_at && billing.plan !== "free" && (
                  <p className="mt-2 text-xs text-muted">
                    Pro access ends{" "}
                    {new Date(billing.expires_at * 1000).toLocaleDateString()}.
                  </p>
                )}
              </div>
              {billing.provider === "stripe" && (
                <button
                  className="btn-ghost"
                  disabled={!billing.enabled || busy}
                  onClick={manageSubscription}
                >
                  Manage subscription
                </button>
              )}
            </div>
            <div className="mt-7 grid gap-5 sm:grid-cols-2">
              <div className="rounded-2xl border border-border p-4">
                <div className="mb-3 flex justify-between text-sm">
                  <span>Interviews</span>
                  <span className="tabular-nums text-muted">
                    {billing.resources.interviews.used} /{" "}
                    {billing.resources.interviews.limit}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-background">
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{
                      width: `${Math.min(100, (billing.resources.interviews.used / billing.resources.interviews.limit) * 100)}%`,
                    }}
                  />
                </div>
              </div>
              <div className="rounded-2xl border border-border p-4">
                <p className="text-sm">Text turns</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums">
                  {billing.resources.text_turns.used}
                </p>
                <p className="mt-1 text-xs text-muted">
                  Answers in text topic practice this month
                </p>
              </div>
            </div>
          </div>
          {!billing.enabled && (
            <p className="mt-5 rounded-xl border border-border bg-surface p-4 text-sm text-muted">
              Paid checkout is not enabled for this installation yet. Your
              current account features remain available.
            </p>
          )}
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">Compare plans</h2>
              <p className="mt-1 text-sm text-muted">
                The same plans, prices, and features listed on the homepage.
              </p>
            </div>
            <div className="flex rounded-full border border-border bg-surface p-1">
              {(["monthly", "yearly"] as const).map((period) => (
                <button
                  key={period}
                  type="button"
                  aria-pressed={billingPeriod === period}
                  onClick={() => setBillingPeriod(period)}
                  className={`rounded-full px-4 py-2 text-sm ${billingPeriod === period ? "bg-accent text-accent-ink" : "text-muted"}`}
                >
                  {period === "monthly" ? "Monthly" : "Yearly"}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {PUBLIC_PLANS.map((plan) => {
              const accountPlan = billing.plans.find(
                (item) => item.id === plan.id,
              );
              const isCurrent = billing.plan === plan.id;
              const canRenew =
                isCurrent &&
                billing.provider === "razorpay_order" &&
                Boolean(billing.expires_at);
              const checkoutReady =
                billing.enabled &&
                Boolean(
                  accountPlan?.available &&
                  accountPlan.periods_available.includes(billingPeriod),
                ) &&
                plan.id !== "free";
              const tierPrice =
                billing.checkout_prices_paise?.[
                  plan.id as "starter" | "pro" | "senior"
                ];
              const displayPrice =
                plan.id !== "free" && tierPrice
                  ? new Intl.NumberFormat("en-IN", {
                      style: "currency",
                      currency: "INR",
                      maximumFractionDigits: 0,
                    }).format(tierPrice[billingPeriod] / 100)
                  : billingPeriod === "monthly"
                    ? plan.monthly
                    : plan.yearly;
              return (
                <article
                  key={plan.id}
                  className={`card relative flex flex-col p-6 ${billing.plan === plan.id ? "!border-accent" : ""} ${plan.highlight ? "ring-1 ring-accent" : ""}`}
                >
                  {plan.highlight && (
                    <span className="absolute -top-3 left-5 rounded-full bg-accent px-3 py-1 text-xs font-medium text-accent-ink">
                      Most popular
                    </span>
                  )}
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-muted">{plan.tag}</p>
                      <h3 className="mt-1 text-lg font-semibold">
                        {plan.name}
                      </h3>
                    </div>
                    {isCurrent && (
                      <span className="badge !text-accent">Your plan</span>
                    )}
                  </div>
                  <p className="my-5 text-2xl font-semibold">
                    {displayPrice}
                    <span className="ml-1 text-sm font-normal text-muted">
                      {plan.id !== "free"
                        ? billingPeriod === "monthly"
                          ? "one-time · 30 days"
                          : "one-time · 365 days"
                        : billingPeriod === "monthly"
                          ? "/mo"
                          : "/yr"}
                    </span>
                  </p>
                  <p className="min-h-14 text-sm leading-6 text-muted">
                    {plan.desc}
                  </p>
                  <ul className="mt-4 flex-1 space-y-3">
                    {plan.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-center gap-2 text-sm text-muted"
                      >
                        <Icon name="check" className="h-4 w-4 text-accent" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <button
                    className={`${plan.highlight ? "btn-primary" : "btn-ghost"} mt-7 w-full`}
                    disabled={
                      busy || (isCurrent && !canRenew) || !checkoutReady
                    }
                    onClick={() => startCheckout(plan.id)}
                  >
                    {isCurrent
                      ? canRenew
                        ? `Renew ${plan.name}`
                        : "Current plan"
                      : checkoutReady
                        ? plan.cta
                        : plan.id === "free"
                          ? "Free plan"
                          : "Not available yet"}
                  </button>
                </article>
              );
            })}
          </div>
          <p className="mt-5 text-xs leading-5 text-muted">
            Text turns count your submitted answers in text topic practice. Plan
            changes are confirmed by the billing provider, so they can take a
            moment to appear.
          </p>
        </>
      )}
    </div>
  );
}
