"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ScoreChart } from "@/components/ScoreChart";
import { api, fmtDate, type Progress } from "@/lib/api";

export default function ProgressPage() {
  const [data, setData] = useState<Progress | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .progress()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  const points = (data?.recent ?? []).flatMap((p) =>
    p.score === null ? [] : [{ ...p, score: p.score }],
  );
  return (
    <div>
      <p className="eyebrow">Make your progress visible</p>
      <h1 className="page-title mt-4">
        Small steps.
        <br />A stronger story.
      </h1>
      <p className="page-subtitle max-w-xl">
        Your completed sessions and practice work, saved in one place. Compare
        similar roles and rounds to make sense of changes in score.
      </p>
      {error && (
        <p className="error-banner mt-6" role="alert">
          {error}
        </p>
      )}
      {!data ? (
        <p className="mt-8 text-sm text-muted">
          {error
            ? "Progress could not be loaded. Refresh to retry."
            : "Loading your progress…"}
        </p>
      ) : (
        <>
          <div className="mt-7 border-t border-border pt-6 grid gap-8 sm:grid-cols-3">
            {[
              ["Completed interviews", data.completed_interviews],
              ["Average practice score", data.average_score ?? "—"],
              [
                "Drills completed",
                `${data.completed_tasks} / ${data.practice_tasks}`,
              ],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="eyebrow">{label}</p>
                <p className="text-3xl font-semibold tracking-tight mt-4">
                  {value}
                </p>
              </div>
            ))}
          </div>
          <section className="mt-7 border-t border-border pt-6">
            <div className="flex flex-wrap justify-between gap-3">
              <h2 className="text-xl font-semibold">Your score over time</h2>
              <span className="text-xs text-muted">
                Latest 100 completed sessions · {data.scored_interviews} scored
                overall
              </span>
            </div>
            <div className="mt-6">
              <ScoreChart points={points} />
            </div>
            <p className="mt-2 text-xs text-muted">
              Sessions with insufficient evidence have no score. Practice scores
              are feedback, not a hiring prediction.
            </p>
          </section>
          <section className="mt-7 border-t border-border pt-6">
            <h2 className="text-xl font-semibold">By interview round</h2>
            {data.rounds.length === 0 ? (
              <p className="mt-5 text-sm text-muted">
                Complete your first interview to see your progress.
              </p>
            ) : (
              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                {data.rounds.map((r) => (
                  <article key={r.id} className="card p-5">
                    <div className="flex justify-between gap-3">
                      <h3 className="text-sm font-medium">{r.name}</h3>
                      <span className="text-sm">
                        {r.average_score ?? "—"}
                        <span className="text-xs text-muted"> / 100</span>
                      </span>
                    </div>
                    <div className="my-4 h-1 bg-border">
                      <div
                        className="h-full bg-foreground"
                        style={{ width: `${r.average_score ?? 0}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted">
                      {r.count} completed sessions
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>
          <section className="mt-7 border-t border-border pt-6">
            <h2 className="text-xl font-semibold">Recent sessions</h2>
            {data.recent.slice(0, 10).map((p) => (
              <Link
                key={p.id}
                href={`/report/${p.id}`}
                className="flex items-center justify-between gap-4 border-b border-border py-5"
              >
                <div>
                  <p className="text-sm font-medium">{p.label}</p>
                  <p className="mt-1 text-xs text-muted">{fmtDate(p.at)}</p>
                </div>
                <span className="shrink-0 text-sm">
                  {p.score === null
                    ? "More evidence needed"
                    : `${p.score} / 100`}{" "}
                  ↗
                </span>
              </Link>
            ))}
          </section>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/setup" className="btn-primary">
              Start a practice session ↗
            </Link>
            <Link href="/practice" className="btn-ghost">
              Your practice plan
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
