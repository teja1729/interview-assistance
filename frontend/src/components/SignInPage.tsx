"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import styles from "./SignInPage.module.css";
import { useAuth } from "@/components/AuthProvider";
import { Icon } from "@/components/Icon";

export function SignInPage({ recruiter = false }: { recruiter?: boolean }) {
  const destination = recruiter ? "/recruiter" : "/dashboard";
  const [config, setConfig] = useState<{
    google_enabled: boolean;
    demo_enabled: boolean;
  } | null>(null);
  const [configFailed, setConfigFailed] = useState(false);
  const [configAttempt, setConfigAttempt] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { refresh, session, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    let active = true;
    api
      .authConfig()
      .then((options) => {
        if (!active) return;
        setConfig(options);
        if (
          new URLSearchParams(window.location.search).get("error") === "google"
        )
          setError("Google sign-in could not be completed. Please try again.");
      })
      .catch(() => {
        if (active) setConfigFailed(true);
      });
    return () => {
      active = false;
    };
  }, [configAttempt]);
  useEffect(() => {
    if (!loading && session) {
      const next = new URLSearchParams(window.location.search).get("next");
      router.replace(
        next &&
          next.startsWith("/") &&
          !next.startsWith("//") &&
          !next.includes("\\")
          ? next
          : destination,
      );
    }
  }, [loading, session, router, destination]);
  async function demo() {
    setBusy(true);
    try {
      await api.demoLogin();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <div className={`${styles.auth} grid min-h-screen lg:grid-cols-2`}>
      <div className="flex flex-col bg-background px-8 py-8 lg:px-16">
        <Link href="/" className={styles.wordmark} aria-label="Suri home">
          suri
          <i aria-hidden="true" />
        </Link>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-20">
          <p className="eyebrow">
            {recruiter ? "Recruiter access" : "Your next chapter"}
          </p>
          <h1 className={`${styles.heading} mt-4`}>
            {recruiter
              ? "Meet your next candidate."
              : "Welcome to better practice."}
          </h1>
          <p className="mt-4 text-sm leading-6 text-muted">
            {recruiter
              ? "Sign in with Google, add your company details, and explore candidates who have chosen to be discovered."
              : "One account for your interviews, feedback, and everything you’re working toward."}
          </p>
          {error && (
            <p role="alert" className="error-banner mt-6">
              {error}
            </p>
          )}
          {configFailed && (
            <div className="mt-8">
              <p role="alert" className="error-banner">
                Sign-in is temporarily unavailable. Please try again.
              </p>
              <button
                className="btn-ghost mt-3 w-full"
                onClick={() => {
                  setConfigFailed(false);
                  setConfigAttempt((attempt) => attempt + 1);
                }}
              >
                Retry sign-in options
              </button>
            </div>
          )}
          {!config && !configFailed && (
            <p role="status" className="mt-8 text-sm text-muted">
              Loading sign-in options…
            </p>
          )}
          {config?.google_enabled && (
            <a
              href="/api/auth/google"
              onClick={(event) => {
                event.preventDefault();
                const next =
                  new URLSearchParams(window.location.search).get("next") ??
                  destination;
                window.location.assign(
                  new URL(
                    `/api/auth/google?next=${encodeURIComponent(next)}`,
                    window.location.origin,
                  ).href,
                );
              }}
              className="btn-ghost mt-8 !py-3.5"
            >
              <span className="text-lg font-bold text-[#4285f4]">G</span>
              Continue with Google
            </a>
          )}
          {config && !config.google_enabled && (
            <div className="mt-8 rounded-xl border border-border bg-background p-4 text-xs leading-5 text-muted">
              Google sign-in is awaiting configuration by the application owner.
              {config?.demo_enabled
                ? " You can explore the complete app below."
                : " Please try again later."}
            </div>
          )}
          {config?.demo_enabled && (
            <button
              className="btn-primary mt-3 !py-3.5"
              onClick={demo}
              disabled={busy}
            >
              {busy ? "Opening your account…" : "Open local test account"}
              <Icon name="arrow" className="h-4 w-4" />
            </button>
          )}
          <p className="mt-5 text-xs leading-5 text-muted">
            {recruiter
              ? "Candidates decide whether to share their resume and email with you. Private interview answers and reports are never shared."
              : "Your resume and answers are processed by the application’s AI provider. Camera preview stays on your device."}
          </p>
          <Link
            href={recruiter ? "/login" : "/recruiter/login"}
            className="mt-6 text-sm underline underline-offset-4"
          >
            {recruiter
              ? "Looking to practise? Candidate sign in"
              : "Hiring? Recruiter sign in"}
          </Link>
          <Link href="/" className="mt-8 text-xs text-accent hover:underline">
            ← Back to home
          </Link>
        </div>
      </div>
      <div className="hidden flex-col justify-center bg-[#151515] p-16 text-white lg:flex">
        <p className="text-xs uppercase tracking-[.2em] text-white/60">
          {recruiter
            ? "Make a thoughtful introduction"
            : "Prepare with intention"}
        </p>
        <h2 className="mt-7 max-w-md text-4xl font-medium leading-tight tracking-tight">
          {recruiter
            ? "A better conversation starts with permission."
            : "Less memorizing. More understanding your own story."}
        </h2>
        <div className="mt-12 space-y-7">
          {(recruiter
            ? [
                "Profiles published by the candidates themselves",
                "An introduction with your company and opportunity",
                "Resume access after the candidate approves",
              ]
            : [
                "Questions grounded in your resume",
                "Follow-ups that challenge your thinking",
                "A clear plan for your next practice session",
              ]
          ).map((s, i) => (
            <div key={s} className="flex items-center gap-4">
              <span className="grid h-8 w-8 place-items-center rounded-full border border-white/20 font-mono text-xs text-white/60">
                0{i + 1}
              </span>
              <span className="text-sm text-white/80">{s}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
