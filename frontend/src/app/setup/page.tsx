"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  type CompanyBrief,
  type Persona,
  type Resume,
  type SavedRoleBrief,
} from "@/lib/api";
import { Icon } from "@/components/Icon";
import { CompanyContext } from "@/components/CompanyContext";

const DURATIONS = [15, 30, 45];

export default function SetupPage() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [companyUrl, setCompanyUrl] = useState("");
  const [companyBrief, setCompanyBrief] = useState<CompanyBrief | undefined>();
  const [researching, setResearching] = useState(false);
  const [language, setLanguage] = useState("en-IN");
  const researchVersion = useRef(0);
  const [years, setYears] = useState(2);
  const [resumeId, setResumeId] = useState<string>("");
  const [jd, setJd] = useState("");
  const [jdSource, setJdSource] = useState<"live" | "demo" | null>(null);
  const [savedBriefs, setSavedBriefs] = useState<SavedRoleBrief[]>([]);
  const [savedNotice, setSavedNotice] = useState("");
  const [custom, setCustom] = useState("");
  const [duration, setDuration] = useState(30);
  const [persona, setPersona] = useState("hiring_manager");

  const [personas, setPersonas] = useState<Persona[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggesting, setSuggesting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const suggestTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    api
      .savedRoleBriefs()
      .then(setSavedBriefs)
      .catch(() => {});
    api
      .personas()
      .then(setPersonas)
      .catch((e) => setError(e.message));
    Promise.resolve().then(() => {
      const focus = new URLSearchParams(window.location.search).get("focus");
      if (focus) setCustom(focus.slice(0, 2000));
    });
    api
      .resumes()
      .then((r) => {
        setResumes(r);
        if (r[0]) setResumeId(r[0].id);
      })
      .catch((e) => setError(e.message));
    return () => {
      if (suggestTimer.current) clearTimeout(suggestTimer.current);
    };
  }, []);

  // Debounced title suggestions, scheduled from the input handler.
  function onTitleChange(value: string) {
    researchVersion.current++;
    const version = researchVersion.current;
    setSavedNotice("");
    setCompanyBrief(undefined);
    setJobTitle(value);
    if (suggestTimer.current) clearTimeout(suggestTimer.current);
    const q = value.trim();
    if (q.length < 3) {
      setSuggestions([]);
      return;
    }
    suggestTimer.current = setTimeout(async () => {
      setSuggesting(true);
      try {
        const { titles } = await api.suggestTitles(q);
        if (version !== researchVersion.current) return;
        setSuggestions(
          titles.filter((t) => t.toLowerCase() !== q.toLowerCase()),
        );
      } catch {
        setSuggestions([]);
      } finally {
        setSuggesting(false);
      }
    }, 700);
  }

  async function generateJD(forceRefresh = false) {
    setGenerating(true);
    setError(null);
    const version = researchVersion.current;
    try {
      const { job_description, demo, company_context, cached, saved_at } =
        await api.generateJD({
          job_title: jobTitle.trim(),
          company: company.trim(),
          experience_years: years,
          company_url: companyUrl.trim(),
          company_research_id: companyBrief?.id,
          force_refresh: forceRefresh,
        });
      if (version !== researchVersion.current) return;
      setCompanyBrief(company_context);
      setJd(job_description);
      setJdSource(demo ? "demo" : "live");
      setSavedNotice(
        `${cached ? "Loaded saved description" : "Description saved"} · ${new Date(saved_at * 1000).toLocaleDateString()}`,
      );
      api
        .savedRoleBriefs()
        .then(setSavedBriefs)
        .catch(() => {});
    } catch (e) {
      if (version === researchVersion.current)
        setError(
          e instanceof Error
            ? e.message
            : "Could not generate a job description",
        );
    } finally {
      setGenerating(false);
    }
  }

  async function researchCompany(forceRefresh = false) {
    setResearching(true);
    setError(null);
    const version = researchVersion.current;
    try {
      const result = await api.researchCompany({
        company: company.trim(),
        job_title: jobTitle.trim(),
        company_url: companyUrl.trim(),
        force_refresh: forceRefresh,
      });
      if (version === researchVersion.current) setCompanyBrief(result);
    } catch (e) {
      if (version === researchVersion.current) setError((e as Error).message);
    } finally {
      setResearching(false);
    }
  }

  async function loadSaved(id: string) {
    if (!id) return;
    setGenerating(true);
    setError(null);
    const version = ++researchVersion.current;
    if (suggestTimer.current) clearTimeout(suggestTimer.current);
    setSuggestions([]);
    try {
      const result = await api.savedRoleBrief(id);
      if (version !== researchVersion.current) return;
      setJobTitle(result.inputs.job_title);
      setCompany(result.inputs.company);
      setCompanyUrl(result.inputs.company_url);
      setYears(result.inputs.experience_years);
      setJd(result.job_description);
      setJdSource(result.demo ? "demo" : "live");
      setCompanyBrief(result.company_context);
      setSavedNotice(
        `Loaded saved description · ${new Date(result.saved_at * 1000).toLocaleDateString()}`,
      );
    } catch (e) {
      if (version === researchVersion.current) setError((e as Error).message);
    } finally {
      setGenerating(false);
    }
  }

  async function start() {
    setStarting(true);
    setError(null);
    try {
      const iv = await api.createInterview({
        job_title: jobTitle.trim(),
        company: company.trim(),
        experience_years: years,
        job_description: jd.trim(),
        custom_instructions: custom.trim(),
        duration_minutes: duration,
        persona,
        resume_id: resumeId || null,
        language,
        company_url: companyUrl.trim(),
        company_research_id: companyBrief?.id,
      });
      router.push(`/interview/${iv.id}`);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not start the interview",
      );
      setStarting(false);
    }
  }

  const canStart =
    jobTitle.trim().length >= 2 &&
    personas.some((p) => p.id === persona) &&
    !starting &&
    !researching &&
    !generating;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="page-title mb-2">New mock interview</h1>
      <p className="mb-6 text-sm text-muted">
        The interviewer is briefed with the job description and your resume,
        then speaks with you in a voice-to-voice practice interview. Captions
        and the transcript are optional.
      </p>

      <div className="mb-6 flex items-center gap-2 text-xs text-accent">
        <Icon name="mic" className="h-4 w-4" />
        Role-focused interview · personalized to your experience
      </div>

      <form
        className="mt-6 space-y-6"
        onSubmit={(e) => {
          e.preventDefault();
          if (canStart) start();
        }}
      >
        {savedBriefs.length > 0 && (
          <div>
            <label className="label" htmlFor="saved-role-brief">
              Use a saved role brief
            </label>
            <select
              id="saved-role-brief"
              className="input"
              value=""
              disabled={generating || starting || researching}
              onChange={(e) => void loadSaved(e.target.value)}
            >
              <option value="">Choose a saved description…</option>
              {savedBriefs.map((brief) => (
                <option key={brief.id} value={brief.id}>
                  {brief.inputs.job_title}
                  {brief.inputs.company
                    ? ` · ${brief.inputs.company}`
                    : ""} ·{" "}
                  {new Date(brief.saved_at * 1000).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label className="label" htmlFor="title">
            Job title
          </label>
          <input
            id="title"
            className="input"
            placeholder="e.g. Agentic AI Engineer"
            value={jobTitle}
            onChange={(e) => onTitleChange(e.target.value)}
            autoFocus
          />
          {(suggestions.length > 0 || suggesting) && (
            <div
              data-testid="suggestions"
              className="mt-2 flex flex-wrap items-center gap-2"
            >
              <span className="text-[11px] uppercase tracking-wide text-muted">
                Suggestions
              </span>
              {suggesting && suggestions.length === 0 && (
                <span className="text-xs text-muted">thinking…</span>
              )}
              {suggestions.map((s) => (
                <button
                  type="button"
                  key={s}
                  className="chip"
                  onClick={() => onTitleChange(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="company">
              Target company
            </label>
            <input
              id="company"
              className="input"
              placeholder="e.g. Google"
              value={company}
              onChange={(e) => {
                setCompany(e.target.value);
                researchVersion.current++;
                setSavedNotice("");
                setCompanyBrief(undefined);
              }}
            />
          </div>
          <div>
            <label className="label" htmlFor="resume">
              Resume
            </label>
            <select
              id="resume"
              className="input"
              value={resumeId}
              onChange={(e) => setResumeId(e.target.value)}
            >
              <option value="">No resume</option>
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
            <Link
              href="/resumes"
              className="mt-1 inline-block text-xs text-accent hover:underline"
            >
              Manage resumes
            </Link>
          </div>
          <div>
            <label className="label" htmlFor="years">
              Experience (years)
            </label>
            <input
              id="years"
              type="number"
              min={0}
              max={50}
              className="input"
              value={years}
              onChange={(e) => {
                researchVersion.current++;
                setSavedNotice("");
                setYears(Math.max(0, Number(e.target.value) || 0));
              }}
            />
          </div>
        </div>

        {company.trim() && (
          <div className="space-y-3">
            <label className="label" htmlFor="company-url">
              Company website or job URL{" "}
              <span className="font-normal text-muted">(optional)</span>
            </label>
            <input
              id="company-url"
              type="url"
              className="input"
              placeholder="https://company.com/careers/role"
              value={companyUrl}
              onChange={(e) => {
                setCompanyUrl(e.target.value);
                researchVersion.current++;
                setSavedNotice("");
                setCompanyBrief(undefined);
              }}
            />
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="chip disabled:opacity-50"
                disabled={
                  researching ||
                  starting ||
                  generating ||
                  jobTitle.trim().length < 2 ||
                  company.trim().length < 2
                }
                onClick={() => void researchCompany()}
              >
                {researching
                  ? "Searching company sources…"
                  : "Research company"}
              </button>
              {companyBrief?.status === "researched" && (
                <button
                  type="button"
                  className="chip"
                  disabled={researching || generating || starting}
                  onClick={() => void researchCompany(true)}
                >
                  Refresh research
                </button>
              )}
              <p className="text-xs text-muted">
                Reuses your saved research. Refresh searches for updates. An
                official URL helps identify the company.
              </p>
            </div>
            <CompanyContext brief={companyBrief} />
          </div>
        )}

        <div>
          <div className="mb-1.5 flex items-center gap-3">
            <label className="label !mb-0" htmlFor="jd">
              Job description
            </label>
            <button
              type="button"
              className="chip !border-accent/40 !text-accent disabled:opacity-50"
              onClick={() => void generateJD()}
              disabled={
                generating ||
                researching ||
                starting ||
                jobTitle.trim().length < 2
              }
            >
              {generating ? "Generating…" : "✦ Generate"}
            </button>
            {jdSource && (
              <button
                type="button"
                className="chip"
                disabled={generating || researching || starting}
                onClick={() => void generateJD(true)}
              >
                Regenerate
              </button>
            )}
          </div>
          <textarea
            id="jd"
            className="input min-h-36 resize-y"
            placeholder="Paste the job description, or generate one from the title."
            value={jd}
            onChange={(e) => {
              setJd(e.target.value);
              setJdSource(null);
              setSavedNotice("");
            }}
          />
          {savedNotice && (
            <p role="status" className="mt-2 text-xs text-accent">
              {savedNotice}
            </p>
          )}
          {jdSource && (
            <p role="status" className="mt-2 text-xs leading-5 text-muted">
              {jdSource === "demo"
                ? "Test fixture: this sample is not a role-specific AI response."
                : "AI-generated practice description. Review and edit it before starting; this is not a verified company vacancy."}
            </p>
          )}
        </div>

        <div className="max-w-sm">
          <label className="label" htmlFor="interview-language">
            Interview language
          </label>
          <select
            id="interview-language"
            className="input mb-5"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {Object.entries({
              "en-IN": "English",
              "hi-IN": "Hindi",
              "bn-IN": "Bengali",
              "ta-IN": "Tamil",
              "te-IN": "Telugu",
              "gu-IN": "Gujarati",
              "kn-IN": "Kannada",
              "ml-IN": "Malayalam",
              "mr-IN": "Marathi",
              "pa-IN": "Punjabi",
              "od-IN": "Odia",
            }).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <div>
            <span className="label">Duration</span>
            <div className="flex gap-2">
              {DURATIONS.map((d) => (
                <button
                  type="button"
                  key={d}
                  onClick={() => setDuration(d)}
                  className={`flex-1 rounded-xl border px-3 py-2.5 text-sm ${duration === d ? "border-accent bg-accent-soft font-medium text-accent" : "border-border bg-surface hover:border-accent/50"}`}
                >
                  {d} min
                </button>
              ))}
            </div>
          </div>
        </div>

        <fieldset>
          <legend className="label">Choose your interviewer</legend>
          <p className="mb-4 text-sm text-muted">
            Pick the round you want to practice. Each interviewer has a
            different focus and follow-up style.
          </p>
          {personas.length === 0 && !error && (
            <p className="text-sm text-muted">Loading interviewers…</p>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            {personas.map((p) => (
              <label
                key={p.id}
                className={`relative cursor-pointer rounded-2xl border p-5 transition focus-within:ring-2 focus-within:ring-accent focus-within:ring-offset-2 ${persona === p.id ? "border-accent bg-accent-soft/60" : "border-border bg-surface hover:border-accent/50"}`}
              >
                <input
                  type="radio"
                  name="persona"
                  value={p.id}
                  aria-label={p.name}
                  aria-describedby={`persona-${p.id}-description`}
                  checked={persona === p.id}
                  onChange={() => setPersona(p.id)}
                  className="sr-only"
                />
                <div className="flex items-start justify-between gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-xl border border-accent/10 bg-accent-soft text-accent">
                    <Icon name={p.icon} />
                  </span>
                  <span
                    aria-hidden
                    className={`grid h-5 w-5 place-items-center rounded-full border ${persona === p.id ? "border-accent bg-accent text-white" : "border-border"}`}
                  >
                    {persona === p.id && (
                      <Icon name="check" className="h-3 w-3" />
                    )}
                  </span>
                </div>
                <p className="mt-4 text-base font-semibold">{p.name}</p>
                <p className="mt-1 text-xs font-medium text-accent">
                  {p.round}
                </p>
                <p
                  id={`persona-${p.id}-description`}
                  className="mt-3 text-sm leading-6 text-muted"
                >
                  {p.description}
                </p>
                <ul
                  className="mt-4 flex flex-wrap gap-1.5"
                  aria-label="Interview focus"
                >
                  {p.focus.map((focus) => (
                    <li
                      key={focus}
                      className="rounded-2xl border border-border/70 bg-surface/70 px-2 py-1 text-[10px] text-muted"
                    >
                      {focus}
                    </li>
                  ))}
                </ul>
                <p className="mt-4 text-xs text-muted">{p.approach}</p>
              </label>
            ))}
          </div>
        </fieldset>

        <div>
          <label className="label" htmlFor="custom">
            Customize your interview{" "}
            <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea
            id="custom"
            className="input min-h-20 resize-y"
            placeholder="e.g. 'Focus on system design', 'Ask more leadership questions'"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
          />
        </div>

        {error && (
          <p className="rounded-xl border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="btn-primary w-full py-3 text-base"
          disabled={!canStart}
        >
          {starting ? "Briefing the interviewer…" : "Start interview"}
        </button>
        {starting && (
          <p className="text-center text-xs text-muted">
            Reading the job description and resume, planning questions. About 10
            to 20 seconds.
          </p>
        )}
      </form>
    </div>
  );
}
