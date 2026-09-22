"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  fmtDate,
  VERDICT_LABEL,
  type InterviewSummary,
  type PracticeTask,
  type Billing,
  type Progress,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Icon } from "@/components/Icon";
import { ScoreChart } from "@/components/ScoreChart";

export default function Dashboard() {
  const { session } = useAuth();
  const [items, setItems] = useState<InterviewSummary[] | null>(null);
  const [tasks, setTasks] = useState<PracticeTask[]>([]);
  const [billing, setBilling] = useState<Billing | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([
      api.interviews(),
      api.practice(),
      api.billing(),
      api.progress(),
    ])
      .then(([i, t, b, p]) => {
        setItems(i);
        setTasks(t);
        setBilling(b);
        setProgress(p);
      })
      .catch((e) => setError(e.message));
  }, []);
  const finished = (items ?? []).filter(
    (i) => i.status === "finished" && i.score !== null,
  );
  const pending = tasks.filter((t) => !t.completed_at);
  const last = finished[0];
  return (
    <div className="enter">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="eyebrow">Your interview preparation</p>
          <h1 className="page-title mt-2">
            Welcome back, {session?.user.name.split(" ")[0]}.
          </h1>
          <p className="page-subtitle">
            Build on your experience. Get a little clearer with every
            conversation.
          </p>
        </div>
        <Link href="/setup" className="btn-primary">
          <Icon name="plus" className="h-4 w-4" />
          New interview
        </Link>
      </div>
      {error && (
        <p role="alert" className="error-banner mb-6">
          {error}
        </p>
      )}
      <div className="mb-7 grid gap-4 sm:grid-cols-3">
        {[
          [
            "Completed interviews",
            progress ? String(progress.completed_interviews) : "—",
            "Every session is a step forward",
            "mic",
          ],
          [
            "Latest practice score",
            last ? String(last.score) : "—",
            last
              ? VERDICT_LABEL[last.verdict!]
              : "Your first debrief starts here",
            "activity",
          ],
          [
            "Your next steps",
            progress
              ? String(progress.practice_tasks - progress.completed_tasks)
              : "—",
            "Focused drills ready to practice",
            "spark",
          ],
        ].map(([label, value, description, icon]) => (
          <div className="card p-5" key={label}>
            <div className="flex items-center justify-between text-xs font-medium text-muted">
              {label}
              <Icon name={icon} className="h-4 w-4" />
            </div>
            <p className="mt-4 text-3xl font-semibold tracking-tight">
              {value}
            </p>
            <p className="mt-2 text-xs text-muted">{description}</p>
          </div>
        ))}
      </div>
      <div className="mb-7 grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <section className="card p-6">
          <div className="flex items-center justify-between">
            <Link href="/progress" className="text-sm font-medium">
              Your progress ↗
            </Link>
            <span className="text-[11px] text-muted">Practice scores</span>
          </div>
          <p className="mt-1 text-xs text-muted">
            Compare similar roles and question sets for a useful trend.
          </p>
          <div className="mt-4">
            <ScoreChart
              points={finished.map((i) => ({
                id: i.id,
                score: i.score!,
                at: i.ended_at ?? i.created_at,
                label: i.job_title,
              }))}
            />
          </div>
        </section>
        <section className="rounded-2xl bg-[#173d36] p-6 text-white">
          <div className="flex items-center gap-2 text-xs text-[#a7d5c4]">
            <Icon name="spark" className="h-4 w-4" />
            Practice with intention
          </div>
          <h2 className="mt-5 text-xl font-medium leading-snug">
            {pending[0]?.title ?? "Your next interview starts with your story."}
          </h2>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-white/65">
            {pending[0]?.instructions ??
              "Bring a real role and your resume. We’ll help you explore the decisions, trade-offs, and results behind your experience."}
          </p>
          <Link
            href={pending.length ? "/practice" : "/setup"}
            className="mt-6 inline-flex items-center gap-2 text-sm text-white"
          >
            {pending.length
              ? "Open your practice plan"
              : "Prepare an interview"}
            <Icon name="arrow" className="h-4 w-4" />
          </Link>
        </section>
      </div>
      <section className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-sm font-semibold">Recent interviews</h2>
          <span className="text-xs text-muted">
            {billing
              ? `${billing.resources.interviews.used} / ${billing.resources.interviews.limit} this month`
              : ""}
          </span>
        </div>
        {items === null ? (
          <p className="p-8 text-sm text-muted">Loading interviews…</p>
        ) : items.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-accent-soft text-accent">
              <Icon name="mic" />
            </div>
            <h3 className="mt-4 text-base font-medium">
              Let’s get your first session on the calendar.
            </h3>
            <p className="mt-2 text-sm text-muted">
              Choose a role, bring your context, and start a conversation.
            </p>
            <Link href="/setup" className="btn-primary mt-5">
              Start your first interview
            </Link>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {items.map((i) => (
              <li key={i.id}>
                <Link
                  href={
                    i.status === "finished" ||
                    i.status === "finishing" ||
                    i.status === "report_failed"
                      ? `/report/${i.id}`
                      : `/interview/${i.id}`
                  }
                  className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-background"
                >
                  <div className="flex min-w-0 items-center gap-4">
                    <span className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-background text-muted sm:flex">
                      <Icon name="mic" className="h-4 w-4" />
                    </span>
                    <div>
                      <p className="text-sm font-medium">
                        {i.job_title}
                        {i.company && (
                          <span className="font-normal text-muted">
                            {" "}
                            · {i.company}
                          </span>
                        )}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        {fmtDate(i.created_at)} · {i.duration_minutes} min ·{" "}
                        {i.turns} answers
                      </p>
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    {i.status === "finished" ? (
                      <>
                        <span className="text-lg font-semibold">
                          {i.score ?? "—"}
                          <span className="text-xs font-normal text-muted">
                            {" "}
                            / 100
                          </span>
                        </span>
                        <p className="text-[11px] text-muted">
                          {i.verdict && VERDICT_LABEL[i.verdict]}
                        </p>
                      </>
                    ) : (
                      <span className="badge">
                        {i.status === "finishing"
                          ? "Preparing report"
                          : i.status === "abandoned"
                            ? "Abandoned"
                            : i.status === "report_failed"
                              ? "Retry report"
                              : "Resume session"}
                      </span>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
