"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  type RecruiterProfile,
  type CandidatePreview,
  type AccessRequest,
} from "@/lib/api";

export default function RecruiterPage() {
  const [profile, setProfile] = useState<RecruiterProfile | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [candidates, setCandidates] = useState<CandidatePreview[]>([]);
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [q, setQ] = useState("");
  const [experience, setExperience] = useState(0);
  const [filter, setFilter] = useState({ q: "", experience: 0 });
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    api
      .recruiterProfile()
      .then((p) => {
        if (active) {
          setProfile(p);
          setCompany(p?.company_name ?? "");
          setTitle(p?.job_title ?? "");
          setLoaded(true);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!profile) return;
    let active = true;
    Promise.all([
      api.candidates(filter.q, filter.experience, offset),
      api.recruiterRequests(),
    ])
      .then(([result, outgoing]) => {
        if (active) {
          setCandidates(result.items);
          setTotal(result.total);
          setRequests(outgoing);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setSearching(false);
      });
    return () => {
      active = false;
    };
  }, [profile, filter, offset]);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setProfile(
        await api.saveRecruiterProfile({
          company_name: company,
          job_title: title,
        }),
      );
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function request(event: React.FormEvent, candidate: CandidatePreview) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await api.requestResume(candidate.id, message);
      setRequests((items) => [...items.filter((x) => x.id !== r.id), r]);
      setSelected("");
      setMessage("");
      setNotice(
        `Request sent to ${candidate.display_name}. Their resume stays private until they approve.`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <p className="eyebrow">Recruiter studio</p>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
        <h1 className="page-title">
          Find your next
          <br />
          conversation.
        </h1>
        {profile && (
          <button className="btn-ghost" onClick={() => setEditing((v) => !v)}>
            Edit recruiter profile
          </button>
        )}
      </div>
      <p className="page-subtitle max-w-xl">
        Explore people who have chosen to be discovered. Introduce your
        opportunity, then request permission to read their resume.
      </p>
      {error && (
        <p role="alert" className="error-banner mt-6">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="mt-6 border border-border p-4 text-sm">
          {notice}
        </p>
      )}
      {!loaded && (
        <p className="mt-8 text-sm text-muted">
          {error
            ? "Could not open your recruiter account. Refresh to retry."
            : "Opening your recruiter account…"}
        </p>
      )}
      {loaded && (!profile || editing) && (
        <form
          className="mt-7 border-t border-border pt-6 max-w-xl space-y-5"
          onSubmit={save}
        >
          <h2 className="text-xl font-semibold">
            {profile ? "Your recruiter profile" : "Introduce yourself"}
          </h2>
          <p className="text-sm leading-6 text-muted">
            Candidates see your Google account name and email, plus the company
            details you provide here, when you request access.
          </p>
          <label className="label">
            Company name
            <input
              className="input mt-2"
              value={company}
              minLength={2}
              maxLength={150}
              required
              onChange={(e) => setCompany(e.target.value)}
            />
          </label>
          <label className="label">
            Your job title
            <input
              className="input mt-2"
              value={title}
              maxLength={150}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <button disabled={busy} className="btn-primary">
            {busy
              ? "Saving…"
              : profile
                ? "Save recruiter profile"
                : "Create recruiter profile"}
          </button>
        </form>
      )}
      {profile && (
        <section className="mt-7 border-t border-border pt-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-xl font-semibold">Candidate directory</h2>
            <Link
              href="/recruiter/requests"
              className="text-sm underline underline-offset-4"
            >
              View your requests ↗
            </Link>
          </div>
          <form
            className="my-7 grid items-end gap-4 sm:grid-cols-[minmax(0,1fr)_auto_auto]"
            onSubmit={(e) => {
              e.preventDefault();
              setSearching(true);
              setError("");
              setOffset(0);
              setFilter({ q, experience });
            }}
          >
            <label className="label min-w-0">
              Role, headline or location
              <input
                className="input mt-2"
                placeholder="Search candidates"
                value={q}
                maxLength={150}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
            <label className="label">
              Minimum experience
              <select
                className="input mt-2"
                value={experience}
                onChange={(e) => setExperience(Number(e.target.value))}
              >
                {[0, 1, 2, 3, 5, 8, 10, 15].map((n) => (
                  <option value={n} key={n}>
                    {n ? `${n}+ years` : "Any experience"}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn-primary mb-1.5" disabled={searching}>
              {searching ? "Searching…" : "Search"}
            </button>
          </form>
          <p className="mb-5 text-xs text-muted">
            {total} published {total === 1 ? "profile" : "profiles"} ·
            Experience and skills are self-reported.
          </p>
          {!candidates.length && (
            <div className="border-y border-border py-16 text-center">
              <h3 className="text-xl font-light">No candidates to show yet.</h3>
              <p className="mt-3 text-sm text-muted">
                Try a broader search. Candidates appear here only after
                publishing their profile.
              </p>
            </div>
          )}
          <div className="grid gap-5 md:grid-cols-2">
            {candidates.map((c) => {
              const access = requests.find(
                (r) => r.candidate_profile_id === c.id,
              );
              const canRequest = !access || access.status === "revoked";
              return (
                <article key={c.id} className="card min-w-0 p-6">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="break-words text-xl font-medium">
                        {c.display_name}
                      </h3>
                      <p className="mt-1 text-sm">{c.target_role}</p>
                    </div>
                    <span className="badge shrink-0">
                      {c.experience_years} years
                    </span>
                  </div>
                  <p className="mt-3 break-words text-sm leading-6 text-muted">
                    {c.headline}
                  </p>
                  {c.location && (
                    <p className="mt-2 text-xs text-muted">{c.location}</p>
                  )}
                  <div className="my-5 flex flex-wrap gap-2">
                    {c.skills.map((s, i) => (
                      <span
                        className="badge max-w-full break-words"
                        key={`${s}-${i}`}
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                  {selected === c.id ? (
                    <form onSubmit={(e) => request(e, c)}>
                      <label className="label">
                        Tell {c.display_name} about the opportunity
                        <textarea
                          className="input mt-2"
                          rows={4}
                          value={message}
                          minLength={10}
                          maxLength={1500}
                          required
                          onChange={(e) => setMessage(e.target.value)}
                        />
                      </label>
                      <div className="mt-3 flex gap-2">
                        <button className="btn-primary" disabled={busy}>
                          Send request
                        </button>
                        <button
                          type="button"
                          className="btn-ghost"
                          disabled={busy}
                          onClick={() => setSelected("")}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : canRequest ? (
                    <button
                      className="btn-ghost"
                      onClick={() => {
                        setSelected(c.id);
                        setMessage("");
                      }}
                    >
                      Request resume
                    </button>
                  ) : (
                    <Link
                      href="/recruiter/requests"
                      className="text-sm underline underline-offset-4"
                    >
                      {access.status === "approved"
                        ? "View approved resume ↗"
                        : access.status === "pending"
                          ? "Awaiting candidate approval"
                          : "Request declined"}
                    </Link>
                  )}
                </article>
              );
            })}
          </div>
          {total > 20 && (
            <div className="mt-6 flex items-center justify-between">
              <button
                className="btn-ghost"
                disabled={offset === 0 || searching}
                onClick={() => {
                  setSearching(true);
                  setOffset((n) => Math.max(0, n - 20));
                }}
              >
                Previous
              </button>
              <span className="text-xs text-muted">
                {offset + 1}–{Math.min(offset + 20, total)} of {total}
              </span>
              <button
                className="btn-ghost"
                disabled={offset + 20 >= total || searching}
                onClick={() => {
                  setSearching(true);
                  setOffset((n) => n + 20);
                }}
              >
                Next
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
