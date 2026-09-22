"use client";
import { useEffect, useState } from "react";
import { api, fmtDate, type AgentRun } from "@/lib/api";
import { Icon } from "@/components/Icon";
export default function ActivityPage() {
  const [runs, setRuns] = useState<AgentRun[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .agentRuns()
      .then(setRuns)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <div className="enter">
      <p className="eyebrow">A clear view of your AI</p>
      <h1 className="page-title mt-2">Agent activity</h1>
      <p className="page-subtitle">
        See which agents worked on your sessions and how each step performed.
      </p>
      <div className="mt-7 grid gap-3 sm:grid-cols-4">
        {[
          ["planner", "Prepares your session"],
          ["interviewer", "Adapts the conversation"],
          ["evaluator", "Reviews the evidence"],
          ["coach", "Builds your practice plan"],
        ].map(([name, desc]) => (
          <div key={name} className="card p-4">
            <Icon name="spark" className="mb-3 h-4 w-4 text-accent" />
            <p className="text-sm font-medium capitalize">{name}</p>
            <p className="mt-1 text-xs text-muted">{desc}</p>
          </div>
        ))}
      </div>
      {error && (
        <p role="alert" className="error-banner mt-6">
          {error}
        </p>
      )}
      <div className="card mt-7 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-border bg-background/60 text-muted">
            <tr>
              {["Agent / time", "Status", "Duration", "Tokens"].map((t) => (
                <th key={t} className="px-5 py-4 font-medium">
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {runs?.map((run) => (
              <tr key={run.id}>
                <td className="px-5 py-4">
                  <p className="font-medium capitalize">{run.agent}</p>
                  <p className="mt-1 text-[10px] text-muted">
                    {fmtDate(run.created_at)}
                  </p>
                </td>
                <td className="px-5 py-4">
                  <span
                    className={`rounded-full px-2 py-1 ${run.status === "succeeded" ? "bg-accent-soft text-accent" : "bg-red-50 text-red-700"}`}
                  >
                    {run.status}
                  </span>
                </td>
                <td className="px-5 py-4 tabular-nums">
                  {(run.duration_ms / 1000).toFixed(1)}s
                </td>
                <td className="px-5 py-4 tabular-nums">
                  {(run.input_tokens + run.output_tokens).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {runs?.length === 0 && (
          <p className="p-10 text-center text-sm text-muted">
            Your agent activity will appear after your first interview or resume
            upload.
          </p>
        )}
        {runs === null && (
          <p className="p-8 text-sm text-muted">Loading activity…</p>
        )}
      </div>
      <p className="mt-4 text-xs text-muted">
        Activity logs contain execution metadata. Your resume and answer text
        are not included.
      </p>
    </div>
  );
}
