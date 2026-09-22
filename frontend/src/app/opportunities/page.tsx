"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
  api,
  fmtDate,
  type CandidateProfileInput,
  type Resume,
  type AccessRequest,
} from "@/lib/api";

/** The draft is local component state; publishing and every consent decision go through the API. */
export default function OpportunitiesPage() {
  const { session } = useAuth();
  const [draft, setDraft] = useState<CandidateProfileInput | null>(null);
  const [skills, setSkills] = useState("");
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [published, setPublished] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([
      api.candidateProfile(),
      api.resumes(),
      api.candidateRequests(),
    ])
      .then(([profile, files, incoming]) => {
        if (!active) return;
        const value = profile ?? {
          display_name: session?.user.name ?? "",
          headline: "",
          target_role: "",
          location: "",
          experience_years: 0,
          skills: [],
          discoverable: false,
          resume_id: null,
        };
        setDraft(value);
        setSkills(value.skills.join(", "));
        setPublished(value.discoverable);
        setResumes(files);
        setRequests(incoming);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [session?.user.name]);
  function field<K extends keyof CandidateProfileInput>(
    key: K,
    value: CandidateProfileInput[K],
  ) {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
  }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!draft) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      // Explicit allowlist prevents read-only server fields from being posted back.
      const {
        display_name,
        headline,
        target_role,
        location,
        experience_years,
        discoverable,
        resume_id,
      } = draft;
      const saved = await api.saveCandidateProfile({
        display_name,
        headline,
        target_role,
        location,
        experience_years,
        discoverable,
        resume_id,
        skills: [
          ...new Set(
            skills
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
          ),
        ],
      });
      setDraft(saved);
      setPublished(saved.discoverable);
      setRequests(await api.candidateRequests());
      setNotice(
        saved.discoverable
          ? "Your profile is visible to signed-in recruiters."
          : "Profile saved privately. Resume access has been revoked.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function decide(id: string, status: "approved" | "denied" | "revoked") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await api.decideRequest(id, status);
      setRequests((items) => items.map((r) => (r.id === id ? updated : r)));
      setNotice(`Request ${status === "denied" ? "declined" : status}.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <p className="eyebrow">Opportunity, on your terms</p>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
        <h1 className="page-title">Get discovered.</h1>
        <span className="badge">
          {published ? "Published to recruiters" : "Private profile"}
        </span>
      </div>
      <p className="page-subtitle max-w-2xl">
        Choose what recruiters can see. Your interview history and reports stay
        private. Your resume and email are shared only with recruiters you
        approve.
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
      {!draft ? (
        <p className="mt-8 text-muted">
          {error
            ? "Your profile could not be loaded. Refresh to retry."
            : "Loading your profile…"}
        </p>
      ) : (
        <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)] mt-10">
          <form onSubmit={save} className="space-y-5">
            <h2 className="text-xl font-medium">Your candidate profile</h2>
            <label className="label">
              Display name
              <input
                className="input mt-2"
                required
                minLength={2}
                maxLength={120}
                value={draft.display_name}
                onChange={(e) => field("display_name", e.target.value)}
              />
            </label>
            <label className="label">
              Headline
              <input
                className="input mt-2"
                maxLength={240}
                placeholder="What should a recruiter know about you?"
                value={draft.headline}
                onChange={(e) => field("headline", e.target.value)}
              />
            </label>
            <label className="label">
              Target role
              <input
                className="input mt-2"
                maxLength={150}
                required={draft.discoverable}
                value={draft.target_role}
                onChange={(e) => field("target_role", e.target.value)}
              />
            </label>
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="label">
                Years of experience
                <input
                  type="number"
                  min={0}
                  max={50}
                  className="input mt-2"
                  value={draft.experience_years}
                  onChange={(e) =>
                    field("experience_years", Number(e.target.value))
                  }
                />
              </label>
              <label className="label">
                Location
                <input
                  maxLength={120}
                  className="input mt-2"
                  value={draft.location}
                  onChange={(e) => field("location", e.target.value)}
                />
              </label>
            </div>
            <label className="label">
              Skills, separated by commas
              <input
                className="input mt-2"
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
              />
              <span className="mt-2 block text-xs font-normal text-muted">
                Up to 20 skills. These are your own descriptions of your
                experience.
              </span>
            </label>
            <label className="label">
              Resume to share after approval
              <select
                className="input mt-2"
                value={draft.resume_id ?? ""}
                onChange={(e) => field("resume_id", e.target.value || null)}
              >
                <option value="">Choose a resume</option>
                {resumes.map((r) => (
                  <option value={r.id} key={r.id} disabled={!r.shareable}>
                    {r.name}
                    {!r.shareable ? " — re-upload to share" : ""}
                  </option>
                ))}
              </select>
            </label>
            <p className="text-xs leading-5 text-muted">
              Recruiters receive the extracted text of this upload after
              approval. Selecting a different resume revokes existing approvals.{" "}
              <Link className="underline" href="/resumes">
                Manage resumes
              </Link>
            </p>
            <label className="flex items-start gap-3 border border-border p-4 text-sm">
              <input
                className="mt-1"
                type="checkbox"
                checked={draft.discoverable}
                onChange={(e) => field("discoverable", e.target.checked)}
              />
              <span>
                Let signed-in recruiters discover my profile
                <span className="mt-1 block text-xs leading-5 text-muted">
                  Publishes the name, role, headline, experience, skills and
                  location above. Turn off and save to hide your profile and
                  revoke access.
                </span>
              </span>
            </label>
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Saving…" : "Save candidate profile"}
            </button>
          </form>
          <section className="border-t border-border pt-6 lg:border-t-0 lg:border-l lg:pl-8 lg:pt-0">
            <p className="eyebrow">Your inbox</p>
            <h2 className="mt-3 text-xl font-semibold">Resume requests</h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              Approval shares your selected resume text and Google account
              email. Company details are supplied by the recruiter. Revoking
              access prevents future reads; it cannot recall a copy already
              saved.
            </p>
            {!requests.length && (
              <p className="mt-8 border-y border-border py-8 text-sm text-muted">
                No requests yet. Publish your profile to become discoverable.
              </p>
            )}
            {requests.map((r) => (
              <article key={r.id} className="mt-6 border-t border-border pt-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium">{r.recruiter_name}</h3>
                  <span className="badge capitalize">
                    {r.status === "denied" ? "declined" : r.status}
                  </span>
                </div>
                <p className="mt-1 text-sm">
                  {r.company_name}
                  {r.job_title && ` · ${r.job_title}`}
                </p>
                <p className="mt-1 break-all text-xs text-muted">
                  {r.recruiter_email} · {fmtDate(r.created_at)}
                </p>
                <p className="my-4 whitespace-pre-wrap break-words text-sm leading-6">
                  {r.message}
                </p>
                <div className="flex flex-wrap gap-2">
                  {r.status === "pending" && (
                    <>
                      <button
                        className="btn-primary"
                        disabled={busy}
                        onClick={() => decide(r.id, "approved")}
                      >
                        Approve resume & email
                      </button>
                      <button
                        className="btn-ghost"
                        disabled={busy}
                        onClick={() => decide(r.id, "denied")}
                      >
                        Decline
                      </button>
                    </>
                  )}
                  {r.status === "approved" && (
                    <button
                      className="btn-ghost"
                      disabled={busy}
                      onClick={() => decide(r.id, "revoked")}
                    >
                      Revoke access
                    </button>
                  )}
                </div>
              </article>
            ))}
          </section>
        </div>
      )}
    </div>
  );
}
