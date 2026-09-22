"use client";

import { useEffect, useRef, useState } from "react";
import { api, fmtDate, type Resume } from "@/lib/api";

export default function ResumesPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [digest, setDigest] = useState<Record<string, string>>({});
  const fileInput = useRef<HTMLInputElement>(null);

  const load = () =>
    api
      .resumes()
      .then(setResumes)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await api.uploadResume(file, name);
      setName("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (
      !confirm(
        "Delete this resume? If used on your candidate profile, this hides that profile and revokes recruiter access. Past interviews retain the resume context already used for their questions and reports.",
      )
    )
      return;
    try {
      await api.deleteResume(id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function toggle(id: string) {
    if (open === id) return setOpen(null);
    setOpen(id);
    if (!digest[id]) {
      try {
        const r = await api.resume(id);
        setDigest((d) => ({ ...d, [id]: r.digest }));
      } catch (e) {
        setError((e as Error).message);
      }
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="page-title mb-2">Resumes</h1>
      <p className="mb-6 text-sm text-muted">
        Upload once. Your private resume library helps every interview probe
        your specific experience. Original uploads are processed in memory and
        not retained.
      </p>

      <form
        onSubmit={upload}
        className="card mb-8 grid gap-3 p-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end"
      >
        <div>
          <label className="label" htmlFor="rname">
            Name
          </label>
          <input
            id="rname"
            className="input"
            placeholder="e.g. Backend 2026"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="rfile">
            File (PDF or .txt)
          </label>
          <input
            id="rfile"
            ref={fileInput}
            type="file"
            accept="application/pdf,text/plain,text/markdown"
            className="input file:mr-3 file:rounded-lg file:border-0 file:bg-accent-soft file:px-3 file:py-1 file:text-sm file:text-accent"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <button className="btn-primary" disabled={!file || busy}>
          {busy ? "Reading…" : "Upload"}
        </button>
        {busy && (
          <p className="text-xs text-muted sm:col-span-3">
            Gemini is reading the resume and writing a digest. About 10 seconds.
          </p>
        )}
        {error && <p className="text-sm text-red-600 sm:col-span-3">{error}</p>}
      </form>

      {resumes.length === 0 ? (
        <p className="text-sm text-muted">No resumes yet.</p>
      ) : (
        <ul className="space-y-3">
          {resumes.map((r) => (
            <li key={r.id} className="card p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium">{r.name}</div>
                  <div className="text-xs text-muted">
                    {r.candidate_name && <span>{r.candidate_name} · </span>}
                    {r.filename} · {fmtDate(r.created_at)}
                  </div>
                  <p className="mt-2 text-sm text-muted">{r.summary}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    className="btn-ghost !px-3 !py-1.5 text-xs"
                    onClick={() => toggle(r.id)}
                  >
                    {open === r.id ? "Hide digest" : "Digest"}
                  </button>
                  <button
                    className="btn-ghost !px-3 !py-1.5 text-xs text-red-600"
                    onClick={() => remove(r.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
              {open === r.id && (
                <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-background p-3 text-xs leading-relaxed">
                  {digest[r.id] ?? "Loading…"}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
