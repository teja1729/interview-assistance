"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type PracticeTask } from "@/lib/api";
import { Icon } from "@/components/Icon";
export default function PracticePage() {
  const [tasks, setTasks] = useState<PracticeTask[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  useEffect(() => {
    api
      .practice()
      .then(setTasks)
      .catch((e) => setError(e.message));
  }, []);
  async function toggle(task: PracticeTask) {
    setBusy(task.id);
    try {
      const updated = await api.completeTask(task.id, !task.completed_at);
      setTasks((ts) =>
        ts!.map((t) => (t.id === task.id ? { ...t, ...updated } : t)),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }
  const done = tasks?.filter((t) => t.completed_at).length ?? 0;
  return (
    <div className="enter">
      <p className="eyebrow">Turn feedback into progress</p>
      <h1 className="page-title mt-2">Your practice plan</h1>
      <p className="page-subtitle">
        Focused exercises from your interviews. Practice, reflect, then try
        again.
      </p>
      {error && (
        <p role="alert" className="error-banner mt-6">
          {error}
        </p>
      )}
      {tasks === null ? (
        <p className="mt-8 text-sm text-muted">Loading your plan…</p>
      ) : tasks.length === 0 ? (
        <div className="card mt-8 p-12 text-center">
          <Icon name="spark" className="mx-auto h-9 w-9 text-accent" />
          <h2 className="mt-4 text-xl font-medium">
            A plan that starts with you.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted">
            Finish your first interview to get targeted exercises based on the
            gaps in your answers.
          </p>
          <Link href="/setup" className="btn-primary mt-6">
            Start an interview
          </Link>
        </div>
      ) : (
        <>
          <div className="card mt-8 flex items-center justify-between p-5">
            <p className="text-sm">
              <span className="font-semibold">
                {done} of {tasks.length}
              </span>{" "}
              exercises completed
            </p>
            <div className="h-2 w-32 rounded-full bg-background">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${(done / tasks.length) * 100}%` }}
              />
            </div>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {tasks.map((task) => (
              <article
                key={task.id}
                className={`card p-6 ${task.completed_at ? "opacity-65" : ""}`}
              >
                <div className="flex items-start gap-4">
                  <button
                    onClick={() => toggle(task)}
                    disabled={busy === task.id}
                    aria-label={
                      task.completed_at
                        ? `Mark ${task.title} incomplete`
                        : `Complete ${task.title}`
                    }
                    aria-pressed={!!task.completed_at}
                    className={`mt-1 grid h-6 w-6 shrink-0 place-items-center rounded-lg border ${task.completed_at ? "border-accent bg-accent text-white" : "border-border hover:border-accent"}`}
                  >
                    {task.completed_at && (
                      <Icon name="check" className="h-4 w-4" />
                    )}
                  </button>
                  <div>
                    <div className="mb-3 flex gap-2">
                      <span className="badge">{task.skill}</span>
                      <span className="badge">{task.minutes} min</span>
                    </div>
                    <h2 className="text-base font-semibold">{task.title}</h2>
                    {(task.source_interview_ids?.length ?? 0) > 1 && (
                      <p className="mt-2 text-xs text-muted">
                        A recurring practice goal across{" "}
                        {task.source_interview_ids!.length} interviews.
                      </p>
                    )}
                    <p className="mt-3 text-sm leading-6 text-muted">
                      {task.instructions}
                    </p>
                    <div className="mt-5 flex flex-wrap gap-5 text-xs">
                      <Link
                        href={`/setup?focus=${encodeURIComponent(task.skill + ": " + task.instructions)}`}
                        className="font-medium text-accent hover:underline"
                      >
                        Practice this in an interview →
                      </Link>
                      <Link
                        href={`/report/${task.interview_id}`}
                        className="text-muted hover:underline"
                      >
                        View original feedback
                      </Link>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
