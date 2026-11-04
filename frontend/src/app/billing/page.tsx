"use client";
import { useEffect, useState } from "react";
import { api, type Billing } from "@/lib/api";
import { Icon } from "@/components/Icon";
import { PUBLIC_PLANS } from "@/lib/plans";
export default function BillingPage() {
  const [billing, setBilling] = useState<Billing | null>(null);
  const [error, setError] = useState("");
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
              </div>
              <button
                className="btn-ghost"
                disabled={!billing.enabled || busy}
                onClick={() => redirect(api.portal)}
              >
                Manage subscription
              </button>
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
              const checkoutReady =
                billing.enabled &&
                Boolean(accountPlan?.available) &&
                plan.id !== "free";
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
                    {billingPeriod === "monthly" ? plan.monthly : plan.yearly}
                    <span className="ml-1 text-sm font-normal text-muted">
                      /{billingPeriod === "monthly" ? "mo" : "yr"}
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
                    disabled={busy || isCurrent || !checkoutReady}
                    onClick={() => redirect(() => api.checkout(plan.id))}
                  >
                    {isCurrent
                      ? "Current plan"
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
