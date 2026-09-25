/* eslint-disable @next/next/no-location-assign-relative-destination -- Signing out clears all private client state. */
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import { Icon } from "./Icon";

const candidateLinks = [
  ["/dashboard", "Overview", "dashboard"],
  ["/setup", "New interview", "mic"],
  ["/resumes", "Resume library", "file"],
  ["/practice", "Practice plan", "spark"],
  ["/progress", "Progress", "activity"],
  ["/opportunities", "Get discovered", "people"],
  ["/activity", "Agent activity", "activity"],
  ["/settings", "Account", "settings"],
  ["/billing", "Plans & usage", "billing"],
];
const recruiterLinks = [
  ["/recruiter", "Candidates", "people"],
  ["/recruiter/requests", "Resume requests", "file"],
  ["/settings", "Account", "settings"],
];
const publicPaths = [
  "/",
  "/login",
  "/signin",
  "/signup",
  "/pricing",
  "/recruiter/login",
];
export function Brand() {
  return (
    <Link
      href="/"
      className="flex items-center gap-2.5 font-semibold tracking-tight"
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background">
        <Icon name="mic" className="h-4 w-4" />
      </span>
      okkra
    </Link>
  );
}
export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const { session, loading } = useAuth();
  const [error, setError] = useState("");
  const isPublic = publicPaths.includes(path);
  const isRecruiter = path.startsWith("/recruiter");
  useEffect(() => {
    if (!isPublic && !loading && !session)
      router.replace(
        `${isRecruiter ? "/recruiter/login" : "/login"}?next=${encodeURIComponent(path + window.location.search)}`,
      );
  }, [isPublic, loading, session, router, path, isRecruiter]);
  if (isPublic) return <>{children}</>;
  if (loading || !session)
    return (
      <div className="grid min-h-screen place-items-center">
        <p className="animate-pulse text-sm text-muted">
          Opening your account…
        </p>
      </div>
    );
  async function signOut() {
    try {
      await api.logout();
      window.location.assign("/");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const links = isRecruiter ? recruiterLinks : candidateLinks;
  return (
    <div className="min-h-screen md:flex">
      <aside className="border-b border-border bg-surface px-5 py-5 md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col md:overflow-y-auto md:border-r md:border-b-0 md:py-7">
        <Brand />
        <nav
          aria-label="Main navigation"
          className="mt-8 flex gap-1 overflow-x-auto md:mb-6 md:flex-col md:gap-1.5 md:overflow-visible"
        >
          {links.map(([href, label, icon]) => (
            <Link
              key={href}
              href={href}
              aria-current={path === href ? "page" : undefined}
              className={`flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${path === href ? "bg-accent-soft font-medium text-accent" : "text-muted hover:bg-background hover:text-foreground"}`}
            >
              <Icon name={icon} className="h-[18px] w-[18px]" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-border pt-5 md:mt-auto md:block">
          <div className="mb-4 flex min-w-0 items-center gap-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent-soft text-sm font-semibold text-accent">
              {session.user.name.slice(0, 1)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">
                {session.user.name}
              </p>
              <p className="truncate text-xs text-muted">
                {session.user.email}
              </p>
            </div>
          </div>
          <Link
            href={isRecruiter ? "/dashboard" : "/recruiter"}
            className="mb-3 block text-xs text-muted hover:text-foreground"
          >
            {isRecruiter ? "Candidate dashboard" : "Recruiter dashboard"}
          </Link>
          <button
            className="flex items-center gap-2 text-xs text-muted hover:text-foreground"
            onClick={signOut}
          >
            <Icon name="logout" className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>
      <div className="min-w-0 flex-1 md:ml-64">
        <header className="flex min-h-16 flex-wrap items-center justify-between gap-3 border-b border-border bg-surface/80 px-5 py-3 lg:px-10">
          <div className="flex items-center gap-2 text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            {isRecruiter
              ? "Find your next candidate."
              : "Your next chapter starts with practice."}
          </div>
          <span className="badge capitalize">
            {isRecruiter
              ? "Recruiter"
              : `${session.account.plan === "free" ? "Starter" : session.account.plan === "team" ? "Legacy" : session.account.plan} plan`}
          </span>
        </header>
        {session.demo && (
          <div className="border-b border-amber-200 bg-amber-50 px-5 py-2 text-center text-xs text-amber-900">
            Local test account · AI responses are synthetic when test fixture
            routing is enabled.
          </div>
        )}
        {error && (
          <p role="alert" className="error-banner m-5">
            {error}
          </p>
        )}
        <main
          key={session.user.id}
          className="mx-auto max-w-7xl px-5 py-8 lg:px-10"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
