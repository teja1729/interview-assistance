import Link from "next/link";
import { Brand } from "@/components/AppShell";
import { Icon } from "@/components/Icon";
export default function PricingPage() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-7">
      <header className="flex items-center justify-between">
        <Brand />
        <Link href="/login" className="btn-ghost">
          Sign in
        </Link>
      </header>
      <main className="py-20">
        <p className="eyebrow text-center">Room to grow</p>
        <h1 className="mt-4 text-center text-4xl font-semibold tracking-tight">
          A plan for your next chapter.
        </h1>
        <p className="mt-4 text-center text-sm text-muted">
          Start with focused practice. Add capacity when you need it.
        </p>
        <div className="mx-auto mt-12 grid max-w-4xl gap-5 md:grid-cols-2">
          {[
            {
              name: "Starter",
              desc: "Build your practice habit.",
              features: [
                "3 interviews / month",
                "150 AI calls / month",
                "Private interview history",
                "Reports and practice plans",
              ],
            },
            {
              name: "Pro",
              desc: "Prepare for an active job search.",
              features: [
                "40 interviews / month",
                "2,000 AI calls / month",
                "Private interview history",
                "Reports and practice plans",
              ],
            },
          ].map((plan, i) => (
            <article
              key={plan.name}
              className={`card p-7 ${i === 1 ? "!border-accent ring-1 ring-accent" : ""}`}
            >
              <p className="text-lg font-semibold">{plan.name}</p>
              <p className="mt-2 text-sm text-muted">{plan.desc}</p>
              <p className="my-7 text-2xl font-semibold">
                {i === 0 ? "Free" : "See checkout"}
              </p>
              <ul className="space-y-4">
                {plan.features.map((f) => (
                  <li key={f} className="flex gap-2 text-sm">
                    <Icon
                      name="check"
                      className="h-4 w-4 shrink-0 text-accent"
                    />
                    {f}
                  </li>
                ))}
              </ul>
              <Link href="/login" className="btn-primary mt-8 w-full">
                {i === 0 ? "Get started" : "View account plans"}
              </Link>
            </article>
          ))}
        </div>
        <p className="mx-auto mt-8 max-w-2xl text-center text-xs leading-5 text-muted">
          Paid plan prices and currency are shown in the secure checkout
          configured by your application operator. Interview setup, resume
          analysis, speech, and feedback count toward AI usage. Limits reset
          each calendar month (UTC).
        </p>
      </main>
    </div>
  );
}
