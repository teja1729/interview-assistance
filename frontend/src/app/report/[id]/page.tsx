"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { CompanyContext } from "@/components/CompanyContext";
import { api, fmtDate, VERDICT_LABEL, type Interview } from "@/lib/api";

const VERDICT_TONE: Record<string, string> = {
  strong_hire:
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  hire: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300",
  lean_hire: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  no_hire: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
};

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [iv, setIv] = useState<Interview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(0);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      try {
        const data = await api.interview(id);
        if (!active) return;
        setIv(data);
        if (data.status === "finishing") timer = setTimeout(load, 2000);
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    void load();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [id, refreshKey]);

  if (error)
    return (
      <div className="error-banner" role="alert">
        {error}
        <button
          className="ml-3 underline"
          onClick={() => {
            setError(null);
            setRefreshKey((v) => v + 1);
          }}
        >
          Retry
        </button>
      </div>
    );
  if (!iv) return <p className="text-sm text-muted">Loading your debrief…</p>;
  if (!iv.report) {
    return (
      <div className="card mx-auto mt-10 max-w-xl p-10 text-center">
        <span className="eyebrow">Your next steps are taking shape</span>
        <h1 className="mt-4 text-2xl font-semibold">
          {iv.status === "finishing"
            ? "Preparing your debrief"
            : iv.status === "report_failed"
              ? "Let’s try that report again"
              : "Your interview is still open"}
        </h1>
        <p className="mt-4 text-sm leading-6 text-muted">
          {iv.status === "finishing"
            ? "Your evaluator is reviewing the evidence, then your coach will build a focused practice plan. You can leave this page; your report will keep processing."
            : "Your saved answers are safe. Continue your session or retry the report below."}
        </p>
        {iv.report_progress && (
          <p role="status" className="mt-3 text-sm text-muted">
            {iv.report_progress.error || iv.report_progress.label}
          </p>
        )}
        {iv.status === "report_failed" ? (
          <button
            className="btn-primary mt-6"
            onClick={async () => {
              try {
                setIv(await api.finish(id));
                setRefreshKey((v) => v + 1);
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Retry report
          </button>
        ) : (
          iv.status !== "finishing" && (
            <Link href={`/interview/${iv.id}`} className="btn-primary mt-6">
              Continue interview
            </Link>
          )
        )}
        <Link href="/dashboard" className="mt-6 block text-sm text-accent">
          Back to overview
        </Link>
      </div>
    );
  }
  const r = iv.report;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6">
        <Link href="/dashboard" className="text-xs text-muted hover:underline">
          ← All interviews
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          {iv.job_title}
          {iv.company && <span className="text-muted"> · {iv.company}</span>}
        </h1>
        <p className="text-xs text-muted">
          {fmtDate(iv.created_at)} · {iv.duration_minutes} min ·{" "}
          {iv.persona_profile?.name ?? "AI interviewer"} ·{" "}
          {iv.turns.filter((turn) => turn.answer).length} answers
        </p>
      </div>

      <p className="mb-5 rounded-xl bg-accent-soft px-4 py-3 text-xs leading-5 text-accent">
        {iv.demo
          ? "Sample report from the demo provider. These scores are fixtures, not a personalized assessment."
          : "Practice feedback based on this conversation, not a hiring prediction. Compare scores only across similar roles and question sets."}
      </p>
      <div className="mb-5">
        <CompanyContext brief={iv.company_context} />
      </div>
      {/* Hero */}
      <div className="card mb-6 grid gap-6 p-6 sm:grid-cols-[auto_1fr] sm:items-center">
        <div className="text-center sm:text-left">
          <div className="text-6xl font-semibold tabular-nums leading-none">
            {r.overall_score ?? "—"}
          </div>
          <div className="mt-1 text-xs uppercase tracking-wide text-muted">
            {r.overall_score === null ? "Insufficient evidence" : "out of 100"}
          </div>
        </div>
        <div>
          <span
            className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${VERDICT_TONE[r.verdict] ?? ""}`}
          >
            {VERDICT_LABEL[r.verdict] ?? r.verdict}
          </span>
          <p className="mt-2 text-sm leading-relaxed">{r.verdict_reason}</p>
        </div>
      </div>

      <p className="mb-6 leading-relaxed">{r.summary}</p>

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <ListCard
          title="Strengths"
          items={r.strengths}
          tone="text-emerald-700 dark:text-emerald-400"
        />
        <ListCard
          title="Gaps"
          items={r.gaps}
          tone="text-red-700 dark:text-red-400"
        />
      </div>

      <section className="card mb-6 p-5">
        <h2 className="mb-3 text-sm font-medium">Communication</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Meter label="Clarity" value={r.communication.clarity} />
          <Meter label="Structure" value={r.communication.structure} />
          {r.communication.confidence !== undefined && (
            <Meter
              label="Confidence (wording)"
              value={r.communication.confidence}
            />
          )}
        </div>
        <p className="mt-3 text-sm text-muted">{r.communication.notes}</p>
        {r.communication.evidence?.map((e, i) => (
          <blockquote
            key={i}
            className="mt-3 border-l-2 border-accent pl-3 text-sm"
          >
            <span className="mr-2 text-xs capitalize text-muted">
              {e.dimension}
            </span>
            {e.quote}
          </blockquote>
        ))}
      </section>

      <section className="mb-6">
        <h2 className="mb-3 text-sm font-medium">Question by question</h2>
        <ol className="space-y-3">
          {r.questions.map((q, i) => (
            <li key={i} className="card overflow-hidden">
              <button
                className="flex w-full items-start justify-between gap-4 p-4 text-left hover:bg-accent-soft/40"
                onClick={() => setOpen(open === i ? null : i)}
                aria-expanded={open === i}
              >
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted">
                    Q{i + 1}
                  </div>
                  <div className="font-medium">{q.question}</div>
                </div>
                <div className="shrink-0 text-right">
                  <div className="text-lg font-semibold tabular-nums">
                    {q.score ?? "—"}
                    <span className="text-xs text-muted">
                      {q.score === null ? "Not assessed" : "/10"}
                    </span>
                  </div>
                </div>
              </button>
              {open === i && (
                <div className="space-y-3 border-t border-border px-4 py-4 text-sm">
                  <Block title="Answer summary">{q.answer_summary}</Block>
                  <Block title="Feedback">{q.feedback}</Block>
                  {!!q.ratings?.length && (
                    <dl className="grid gap-3 sm:grid-cols-2">
                      {q.ratings.map((rating) => (
                        <div
                          key={rating.criterion}
                          className="rounded-lg bg-background p-3"
                        >
                          <dt className="text-xs font-medium capitalize">
                            {rating.criterion.replaceAll("_", " ")} ·{" "}
                            {rating.score === null
                              ? "Not applicable"
                              : `${rating.score}/4`}
                          </dt>
                          <dd className="mt-1 text-sm text-muted">
                            {rating.reason}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  {q.evidence?.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs uppercase tracking-wide text-muted">
                        Evidence from your answers
                      </p>
                      {q.evidence.map((quote, index) => (
                        <blockquote
                          key={index}
                          className="mb-2 border-l-2 border-accent pl-3 text-sm italic text-muted"
                        >
                          {quote}
                        </blockquote>
                      ))}
                    </div>
                  )}
                  <Block title="A strong answer">{q.ideal_answer}</Block>
                </div>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section className="card mb-8 p-5">
        <h2 className="mb-2 text-sm font-medium">Drill next</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm">
          {r.drill_next.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
        </ol>
      </section>

      <details className="mb-8">
        <summary className="cursor-pointer text-sm text-muted">
          Full transcript
        </summary>
        <ol className="mt-3 space-y-3 text-sm">
          {iv.turns.map((t, i) => (
            <li key={i}>
              <p className="text-muted">{t.question}</p>
              <p className="mt-1 rounded-lg bg-accent-soft/60 px-2.5 py-1.5">
                {t.answer}
              </p>
            </li>
          ))}
        </ol>
      </details>

      <div className="flex gap-3">
        <Link href="/practice" className="btn-primary">
          Open your practice plan
        </Link>
        <Link href="/setup" className="btn-ghost">
          Practise again
        </Link>
        <Link href="/dashboard" className="btn-ghost">
          Back home
        </Link>
      </div>
    </div>
  );
}

function ListCard({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: string;
}) {
  return (
    <div className="card p-5">
      <h2 className={`mb-2 text-sm font-medium ${tone}`}>{title}</h2>
      {items.length === 0 ? (
        <p className="text-sm text-muted">Nothing noted.</p>
      ) : (
        <ul className="space-y-1.5 text-sm">
          {items.map((s, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-muted">•</span>
              <span>{s}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Meter({ label, value }: { label: string; value: number | null }) {
  if (value === null)
    return (
      <div>
        <p className="text-xs">{label}</p>
        <p className="mt-1 text-sm text-muted">Insufficient evidence</p>
      </div>
    );
  const v = Math.max(0, Math.min(10, value));
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span>{label}</span>
        <span className="tabular-nums text-muted">{v}/10</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-background"
        role="meter"
        aria-valuenow={v}
        aria-valuemin={0}
        aria-valuemax={10}
        aria-label={label}
      >
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${v * 10}%` }}
        />
      </div>
    </div>
  );
}

function Block({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-1 text-xs uppercase tracking-wide text-muted">
        {title}
      </div>
      <p className="leading-relaxed">{children}</p>
    </div>
  );
}
