"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, fmtDate, type AccessRequest, type SharedResume } from "@/lib/api";

export default function RecruiterRequestsPage() {
  const [requests, setRequests] = useState<AccessRequest[] | null>(null);
  const [resume, setResume] = useState<SharedResume | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .recruiterRequests()
      .then(setRequests)
      .catch((e) => setError(e.message));
  }, []);
  async function view(id: string) {
    setBusy(true);
    setResume(null);
    setError("");
    try {
      setResume(await api.sharedResume(id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <p className="eyebrow">Connections</p>
      <h1 className="page-title mt-4">Your resume requests.</h1>
      <p className="page-subtitle">
        Access is checked each time you open a resume. Candidates can withdraw
        permission at any time.
      </p>
      <Link className="mt-5 inline-block text-sm underline" href="/recruiter">
        ← Candidate directory
      </Link>
      {error && (
        <p role="alert" className="error-banner mt-6">
          {error}
        </p>
      )}
      {requests === null ? (
        <p className="mt-8 text-sm text-muted">
          {error
            ? "Complete your recruiter profile or refresh to retry."
            : "Loading requests…"}
        </p>
      ) : requests.length === 0 ? (
        <p className="mt-7 border-t border-border pt-6 text-sm text-muted">
          No requests yet. Browse candidates and introduce an opportunity.
        </p>
      ) : (
        <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)] mt-8">
          <section>
            {requests.map((r) => (
              <article className="border-t border-border py-6" key={r.id}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-xl font-medium">{r.candidate_name}</h2>
                  <span className="badge capitalize">
                    {r.status === "denied" ? "declined" : r.status}
                  </span>
                </div>
                <p className="mt-2 text-xs text-muted">
                  Requested {fmtDate(r.created_at)} · {r.company_name}
                </p>
                <p className="my-4 whitespace-pre-wrap break-words text-sm leading-6">
                  {r.message}
                </p>
                {r.status === "approved" && (
                  <button
                    className="btn-primary"
                    disabled={busy}
                    onClick={() => view(r.id)}
                  >
                    View resume & contact
                  </button>
                )}
              </article>
            ))}
          </section>
          <section aria-live="polite">
            {busy && <p className="text-sm">Checking access…</p>}
            {resume ? (
              <article className="card p-6">
                <div className="flex items-start justify-between gap-4">
                  <h2 className="text-xl font-medium">
                    {resume.candidate_name}
                  </h2>
                  <button
                    className="text-xs underline"
                    onClick={() => setResume(null)}
                  >
                    Close
                  </button>
                </div>
                <a
                  href={`mailto:${resume.email}`}
                  className="mt-3 block break-all text-sm underline"
                >
                  {resume.email}
                </a>
                <p className="my-5 text-xs text-muted">
                  {resume.resume_name} · Text extracted from the candidate’s
                  upload
                </p>
                <div className="whitespace-pre-wrap break-words text-sm leading-7">
                  {resume.text}
                </div>
              </article>
            ) : (
              !busy && (
                <p className="border border-border p-6 text-sm leading-6 text-muted">
                  An approved candidate’s resume and contact details will appear
                  here when you open their request.
                </p>
              )
            )}
          </section>
        </div>
      )}
    </div>
  );
}
