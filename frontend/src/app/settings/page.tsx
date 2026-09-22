/* eslint-disable @next/next/no-location-assign-relative-destination -- Signing out clears all private client state. */
"use client";

import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const { session } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signOutEverywhere() {
    setBusy(true);
    setError("");
    try {
      await api.logoutAll();
      window.location.assign("/login");
    } catch (error) {
      setError((error as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="enter max-w-3xl">
      <p className="eyebrow">Your account</p>
      <h1 className="page-title mt-2">Account settings</h1>
      <p className="page-subtitle">Your profile and sign-in security.</p>
      {error && (
        <p role="alert" className="error-banner mt-6">
          {error}
        </p>
      )}
      <section className="card mt-8 p-6">
        <h2 className="text-base font-semibold">Profile</h2>
        <dl className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted">Name</dt>
            <dd className="mt-1 text-sm font-medium">{session?.user.name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Email</dt>
            <dd className="mt-1 break-all text-sm font-medium">
              {session?.user.email}
            </dd>
          </div>
        </dl>
        <p className="mt-5 text-sm text-muted">
          {session?.demo
            ? "Local test account."
            : "Your name and email are updated from Google when you sign in."}
        </p>
      </section>
      <section className="card mt-5 p-6">
        <h2 className="text-base font-semibold">Account security</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Sign out on every device, including this one. Your interviews,
          resumes, and practice plans stay saved.
        </p>
        <button
          className="btn-ghost mt-5"
          disabled={busy}
          onClick={signOutEverywhere}
        >
          {busy ? "Signing out…" : "Sign out on all devices"}
        </button>
      </section>
    </div>
  );
}
