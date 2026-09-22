"use client";
import { useEffect, useState } from "react";
import { api, type Billing } from "@/lib/api";
import { Icon } from "@/components/Icon";
export default function BillingPage() {
  const [billing, setBilling] = useState<Billing | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
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
        Track your usage and find the right plan for your preparation.
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
                  {billing.plan_name}
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
            <div className="mt-7 grid gap-6 sm:grid-cols-2">
              {Object.entries(billing.resources).map(([key, value]) => (
                <div key={key}>
                  <div className="mb-3 flex justify-between text-sm">
                    <span>
                      {key === "interviews" ? "Interviews" : "AI calls"}
                    </span>
                    <span className="tabular-nums text-muted">
                      {value.used} / {value.limit}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-background">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{
                        width: `${Math.min(100, (value.used / value.limit) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          {!billing.enabled && (
            <p className="mt-5 rounded-xl border border-border bg-surface p-4 text-sm text-muted">
              Paid checkout is not enabled for this installation yet. Your
              current account features remain available.
            </p>
          )}
          <div className="mt-7 grid gap-5 md:grid-cols-2">
            {billing.plans.map((plan) => (
              <article
                key={plan.id}
                className={`card p-6 ${billing.plan === plan.id ? "!border-accent" : ""}`}
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">{plan.name}</h2>
                  {billing.plan === plan.id && (
                    <span className="badge !text-accent">Your plan</span>
                  )}
                </div>
                <p className="my-6 text-2xl font-semibold">
                  {plan.id === "free" ? "Free" : "Price at checkout"}
                </p>
                <ul className="space-y-3">
                  {[
                    `${plan.interviews} interviews / month`,
                    `${plan.ai_calls.toLocaleString()} AI calls / month`,
                    "Feedback and practice plans",
                  ].map((f) => (
                    <li
                      key={f}
                      className="flex items-center gap-2 text-sm text-muted"
                    >
                      <Icon name="check" className="h-4 w-4 text-accent" />
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  className="btn-primary mt-7 w-full"
                  disabled={
                    busy ||
                    !billing.enabled ||
                    !plan.available ||
                    billing.plan === plan.id ||
                    plan.id === "free"
                  }
                  onClick={() => redirect(() => api.checkout(plan.id))}
                >
                  {billing.plan === plan.id
                    ? "Current plan"
                    : plan.id === "free"
                      ? "Manage in portal"
                      : "Continue to checkout"}
                </button>
              </article>
            ))}
          </div>
          <p className="mt-5 text-xs leading-5 text-muted">
            AI calls include preparation, resume analysis, interview turns,
            speech, and report generation. Failed attempts also count toward
            usage. Plan changes are confirmed by the billing provider, so they
            can take a moment to appear.
          </p>
        </>
      )}
    </div>
  );
}
