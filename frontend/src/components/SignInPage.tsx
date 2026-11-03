"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import styles from "./SignInPage.module.css";

type Props = {
  recruiter?: boolean;
  signup?: boolean;
};

export function SignInPage({ recruiter = false, signup = false }: Props) {
  const destination = recruiter ? "/recruiter" : "/dashboard";
  const [config, setConfig] = useState<{
    google_enabled: boolean;
    linkedin_enabled: boolean;
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
        const authError = new URLSearchParams(window.location.search).get(
          "error",
        );
        if (authError === "google")
          setError("Google sign-in could not be completed. Please try again.");
        if (authError === "linkedin")
          setError(
            "LinkedIn sign-in could not be completed. Please try again.",
          );
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

  function startOAuth(provider: "google" | "linkedin") {
    const next =
      new URLSearchParams(window.location.search).get("next") ?? destination;
    window.location.assign(
      new URL(
        `/api/auth/${provider}?next=${encodeURIComponent(next)}`,
        window.location.origin,
      ).href,
    );
  }

  const heading = signup
    ? "Get started free"
    : recruiter
      ? "Meet your next candidate."
      : "Welcome back.";
  const intro = signup
    ? "Create your account securely with Google or LinkedIn."
    : recruiter
      ? "Sign in to introduce your company and explore candidates who have chosen to be discovered."
      : "Continue your interview practice and see the progress you have made.";

  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="auth-heading">
        <Link href="/" className={styles.brand} aria-label="Okkra home">
          <Image
            src="/okkra-logo.svg"
            alt="Okkra"
            width={145}
            height={54}
            className={styles.brandLogo}
            priority
          />
        </Link>

        <div className={styles.header}>
          <p className={styles.eyebrow}>
            {recruiter
              ? "RECRUITER ACCESS"
              : signup
                ? "CREATE ACCOUNT"
                : "WELCOME BACK"}
          </p>
          <h1 className={styles.heading} id="auth-heading">
            {heading}
          </h1>
          <p className={styles.description}>{intro}</p>
        </div>

        {error && (
          <p className={styles.errorBox} role="alert">
            {error}
          </p>
        )}

        {configFailed ? (
          <div className={styles.configMessage}>
            <p role="alert">Sign-in options could not be loaded.</p>
            <button
              className={styles.textButton}
              onClick={() => {
                setConfigFailed(false);
                setConfigAttempt((attempt) => attempt + 1);
              }}
            >
              Try again
            </button>
          </div>
        ) : !config ? (
          <p className={styles.loading} role="status">
            Loading sign-in options…
          </p>
        ) : (
          <div className={styles.providers} aria-busy={busy}>
            {config.google_enabled && (
              <button
                type="button"
                className={styles.providerButton}
                onClick={() => startOAuth("google")}
              >
                <span className={styles.googleMark} aria-hidden="true">
                  G
                </span>
                Continue with Google
              </button>
            )}
            {config.linkedin_enabled && (
              <button
                type="button"
                className={styles.providerButton}
                onClick={() => startOAuth("linkedin")}
              >
                <span className={styles.linkedinMark} aria-hidden="true">
                  in
                </span>
                Continue with LinkedIn
              </button>
            )}
            {!config.google_enabled && !config.linkedin_enabled && (
              <p className={styles.configMessage} role="status">
                Sign-in is temporarily unavailable. Please try again later.
              </p>
            )}
            {config.demo_enabled && (
              <button
                type="button"
                className={styles.demoButton}
                onClick={demo}
                disabled={busy}
              >
                {busy ? "Opening your account…" : "Open local test account"}
              </button>
            )}
          </div>
        )}

        <div className={styles.dividerRow}>
          <span />
          <span>SECURE SIGN-IN</span>
          <span />
        </div>

        <p className={styles.switchText}>
          {recruiter ? (
            <>
              Looking to practise? <Link href="/login">Candidate sign in</Link>
            </>
          ) : signup ? (
            <>
              Already have an account? <Link href="/login">Sign in</Link>
            </>
          ) : (
            <>
              New to Okkra? <Link href="/signup">Create an account</Link>
            </>
          )}
        </p>
        <p className={styles.privacyNote}>
          {recruiter
            ? "Candidates choose whether to share their profile. Resume access requires their approval."
            : "Your interview answers and reports stay private. You control whether recruiters can discover your profile."}
        </p>
        <Link href="/" className={styles.backLink}>
          ← Back to home
        </Link>
      </section>

      <aside className={styles.sidePanel}>
        <div className={styles.sidePanelInner}>
          <p className={styles.sideEyebrow}>FROM PRACTICE TO OFFER</p>
          {recruiter ? (
            <>
              <h2 className={styles.sideHeading}>
                Good hiring starts with permission.
              </h2>
              <div className={styles.sideSteps}>
                {[
                  "Candidates choose to publish their profile",
                  "You introduce your company and opportunity",
                  "Resume access follows candidate approval",
                ].map((step, index) => (
                  <div className={styles.sideStep} key={step}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <p>{step}</p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <h2 className={styles.sideHeading}>
                Make your experience easier to talk about.
              </h2>
              <div className={styles.sideSteps}>
                {[
                  "Practise with questions shaped around your role",
                  "Get feedback grounded in your own answers",
                  "Choose if and when recruiters can discover you",
                ].map((step, index) => (
                  <div className={styles.sideStep} key={step}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <p>{step}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </aside>
    </main>
  );
}
