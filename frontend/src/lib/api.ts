/** Browser API boundary. Same-origin proxy keeps credentials out of localStorage and URLs.
 * All authenticated mutations carry the server-issued CSRF token. Agent/provider secrets
 * are never part of these contracts. See docs/API.md before changing endpoint behavior.
 */
export const API = "";
export type Persona = {
  id: string;
  name: string;
  round: string;
  description: string;
  approach: string;
  focus: string[];
  icon: string;
};
export type CompanyBrief = {
  id?: string | null;
  company: string;
  status: "researched" | "unavailable" | "not_requested";
  facts: { text: string; source_ids: string[] }[];
  sources: { id: string; title: string; url: string }[];
  researched_at: number | null;
  note: string;
  search_suggestions: string;
  cached?: boolean;
};
export type SavedRoleBrief = {
  id: string;
  saved_at: number;
  inputs: {
    job_title: string;
    company: string;
    company_url: string;
    experience_years: number;
  };
};
export type RoleBrief = SavedRoleBrief & {
  job_description: string;
  demo: boolean;
  company_context: CompanyBrief;
  cached: boolean;
};
export type Resume = {
  id: string;
  name: string;
  filename: string;
  mime: string;
  candidate_name: string;
  summary: string;
  created_at: number;
  shareable?: boolean;
};
export type RecruiterProfile = {
  company_name: string;
  job_title: string;
  created_at: number;
};
export type CandidateProfileInput = {
  display_name: string;
  headline: string;
  target_role: string;
  location: string;
  experience_years: number;
  skills: string[];
  discoverable: boolean;
  resume_id: string | null;
};
export type CandidatePreview = Omit<
  CandidateProfileInput,
  "discoverable" | "resume_id"
> & { id: string; updated_at: number };
export type CandidateProfile = CandidateProfileInput & {
  id: string;
  updated_at: number;
};
export type AccessRequest = {
  id: string;
  candidate_profile_id: string;
  candidate_name?: string;
  recruiter_name: string;
  recruiter_email: string;
  company_name: string;
  job_title: string;
  message: string;
  status: "pending" | "approved" | "denied" | "revoked";
  created_at: number;
  decided_at: number | null;
};
export type SharedResume = {
  candidate_name: string;
  email: string;
  resume_name: string;
  text: string;
};
export type Progress = {
  completed_interviews: number;
  scored_interviews: number;
  average_score: number | null;
  practice_tasks: number;
  completed_tasks: number;
  rounds: {
    id: string;
    name: string;
    count: number;
    average_score: number | null;
  }[];
  recent: {
    id: string;
    score: number | null;
    at: number;
    label: string;
    persona: string;
  }[];
};
export type Turn = {
  id?: string;
  topic?: number;
  question: string;
  answer: string | null;
  at: number;
};
export type Report = {
  overall_score: number | null;
  verdict:
    "strong_hire" | "hire" | "lean_hire" | "no_hire" | "insufficient_evidence";
  assessment_version?: number;
  rubric_definition?: {
    id: string;
    criteria: { id: string; weight: number; description: string }[];
  } | null;
  verdict_reason: string;
  summary: string;
  strengths: string[];
  gaps: string[];
  questions: {
    topic: number;
    question: string;
    answer_summary: string;
    score: number | null;
    feedback: string;
    ideal_answer: string;
    evidence: string[];
    ratings?: {
      criterion: string;
      score: number | null;
      reason: string;
      evidence_indices: number[];
    }[];
  }[];
  communication: {
    clarity: number | null;
    structure: number | null;
    confidence?: number;
    notes: string;
    evidence?: { dimension: string; answer_id: string; quote: string }[];
  };
  drill_next: string[];
};
export type InterviewStatus =
  | "lobby"
  | "active"
  | "complete"
  | "finishing"
  | "finished"
  | "report_failed"
  | "abandoned";
export type Interview = {
  id: string;
  user_id: string;
  created_at: number;
  started_at: number | null;
  ended_at: number | null;
  status: InterviewStatus;
  version: number;
  job_title: string;
  company: string;
  company_context: CompanyBrief;
  language: string;
  experience_years: number;
  job_description: string;
  custom_instructions: string;
  preference_notice?: string | null;
  duration_minutes: number;
  persona: string;
  persona_profile: Persona;
  resume_id: string | null;
  plan: { focus_areas: string[] };
  turns: Turn[];
  closing_remark: string | null;
  report: Report | null;
  report_progress?: {
    completed_steps: number;
    label: string;
    error: string | null;
  } | null;
  score: number | null;
  remaining_seconds: number;
  current_question: string | null;
  demo: boolean;
};
export type InterviewSummary = Pick<
  Interview,
  | "id"
  | "user_id"
  | "created_at"
  | "ended_at"
  | "status"
  | "job_title"
  | "company"
  | "persona"
  | "duration_minutes"
  | "score"
> & { verdict: Report["verdict"] | null; turns: number };
export type TurnResult = {
  transcript: string;
  reply: string;
  done: boolean;
  repeat: boolean;
  remaining_seconds: number;
  version: number;
};
export type User = {
  id: string;
  name: string;
  email: string;
  avatar_url: string;
};
export type AuthSession = {
  user: User;
  account: { id: string; plan: string };
  csrf_token: string;
  demo: boolean;
};
export type Usage = {
  local_development_allowance?: boolean;
  plan: string;
  plan_name: string;
  period: string;
  resources: Record<"interviews" | "ai_calls", { used: number; limit: number }>;
};
export type PracticeTask = {
  id: string;
  interview_id: string;
  title: string;
  instructions: string;
  skill: string;
  skill_id?: string | null;
  source_interview_ids?: string[];
  minutes: number;
  completed_at: number | null;
};
export type AgentRun = {
  id: string;
  interview_id: string | null;
  agent: string;
  prompt_version: string;
  provider: string;
  model: string;
  status: string;
  duration_ms: number;
  input_tokens: number;
  output_tokens: number;
  error_code: string | null;
  created_at: number;
};
export type Billing = Usage & {
  status: string;
  enabled: boolean;
  plans: {
    id: string;
    name: string;
    interviews: number;
    ai_calls: number;
    available: boolean;
  }[];
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
let csrf: string | null = null;
let authRequest: Promise<AuthSession> | null = null;
async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : "Please check the supplied fields and try again.";
    } catch {
      /* gateway response */
    }
    if (response.status === 401) {
      csrf = null;
      if (typeof window !== "undefined")
        window.dispatchEvent(new Event("session-expired"));
    }
    throw new ApiError(response.status, detail);
  }
  return response.json();
}
export async function getSession(): Promise<AuthSession> {
  if (!authRequest) {
    authRequest = fetch("/api/auth/me", {
      credentials: "include",
      cache: "no-store",
    })
      .then(handle<AuthSession>)
      .then((session) => {
        csrf = session.csrf_token;
        return session;
      })
      .finally(() => {
        authRequest = null;
      });
  }
  return authRequest;
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Requested-With", "interview-studio");
  if (
    init.method &&
    !["GET", "HEAD"].includes(init.method) &&
    path !== "/auth/demo"
  ) {
    if (!csrf) await getSession();
    headers.set("X-CSRF-Token", csrf!);
  }
  return fetch(`/api${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
    signal: init.signal ?? AbortSignal.timeout(150_000),
  }).then(handle<T>);
}
const json = (body: unknown, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  progress: () => request<Progress>("/progress"),
  recruiterProfile: () =>
    request<RecruiterProfile | null>("/recruiter/profile"),
  saveRecruiterProfile: (body: { company_name: string; job_title: string }) =>
    request<RecruiterProfile>("/recruiter/profile", json(body, "PUT")),
  candidateProfile: () =>
    request<CandidateProfile | null>("/candidate-profile"),
  saveCandidateProfile: (body: CandidateProfileInput) =>
    request<CandidateProfile>("/candidate-profile", json(body, "PUT")),
  candidates: (q: string, experience: number, offset = 0) =>
    request<{ items: CandidatePreview[]; total: number }>(
      `/recruiter/candidates?${new URLSearchParams({ q, min_experience: String(experience), offset: String(offset) })}`,
    ),
  requestResume: (id: string, message: string) =>
    request<AccessRequest>(
      `/recruiter/candidates/${id}/request`,
      json({ message }),
    ),
  recruiterRequests: () => request<AccessRequest[]>("/recruiter/requests"),
  candidateRequests: () => request<AccessRequest[]>("/candidate-requests"),
  decideRequest: (id: string, status: "approved" | "denied" | "revoked") =>
    request<AccessRequest>(
      `/candidate-requests/${id}`,
      json({ status }, "PATCH"),
    ),
  sharedResume: (id: string) =>
    request<SharedResume>(`/recruiter/requests/${id}/resume`),
  session: getSession,
  authConfig: () =>
    request<{
      google_enabled: boolean;
      linkedin_enabled: boolean;
      demo_enabled: boolean;
    }>("/auth/config", {
      signal: AbortSignal.timeout(10_000),
    }),
  demoLogin: () => request<{ ok: true }>("/auth/demo", { method: "POST" }),
  logout: () =>
    request("/auth/logout", { method: "POST" }).then(() => {
      csrf = null;
    }),
  logoutAll: () =>
    request("/auth/logout-all", { method: "POST" }).then(() => {
      csrf = null;
    }),
  capabilities: () =>
    request<{ voice_input: boolean; cloud_voice: boolean }>("/capabilities"),
  personas: () => request<Persona[]>("/personas"),
  researchCompany: (body: {
    company: string;
    job_title: string;
    company_url: string;
    force_refresh?: boolean;
  }) => request<CompanyBrief>("/company-research", json(body)),
  suggestTitles: (job_title: string) =>
    request<{ titles: string[] }>("/suggest/titles", json({ job_title })),
  generateJD: (body: {
    job_title: string;
    company: string;
    experience_years: number;
    company_url?: string;
    company_research_id?: string | null;
    force_refresh?: boolean;
  }) => request<RoleBrief>("/suggest/job-description", json(body)),
  savedRoleBriefs: () => request<SavedRoleBrief[]>("/setup/job-descriptions"),
  savedRoleBrief: (id: string) =>
    request<RoleBrief>(`/setup/job-descriptions/${id}`),
  resumes: () => request<Resume[]>("/resumes"),
  resume: (id: string) =>
    request<Resume & { digest: string }>(`/resumes/${id}`),
  uploadResume: (file: File, name: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name);
    return request<Resume>("/resumes", { method: "POST", body: fd });
  },
  deleteResume: (id: string) => request(`/resumes/${id}`, { method: "DELETE" }),
  interviews: (offset = 0) =>
    request<InterviewSummary[]>(`/interviews?offset=${offset}`),
  interview: (id: string) => request<Interview>(`/interviews/${id}`),
  createInterview: (body: {
    job_title: string;
    company: string;
    experience_years: number;
    job_description: string;
    custom_instructions: string;
    duration_minutes: number;
    persona: string;
    resume_id: string | null;
    language?: string;
    company_url?: string;
    company_research_id?: string | null;
  }) => request<Interview>("/interviews", json(body)),
  join: (id: string) =>
    request<Interview>(`/interviews/${id}/join`, { method: "POST" }),
  audioTurn: (id: string, wav: Blob, version: number, requestId: string) => {
    const fd = new FormData();
    fd.append("audio", wav, "answer.wav");
    fd.append("version", String(version));
    fd.append("request_id", requestId);
    return request<TurnResult>(`/interviews/${id}/turn`, {
      method: "POST",
      body: fd,
    });
  },
  textTurn: (id: string, text: string, version: number, requestId: string) =>
    request<TurnResult>(
      `/interviews/${id}/turn-text`,
      json({ text, version, request_id: requestId }),
    ),
  finish: (id: string) =>
    request<Interview>(`/interviews/${id}/finish`, { method: "POST" }),
  abandon: (id: string) =>
    request(`/interviews/${id}/abandon`, { method: "POST" }),
  tts: async (
    text: string,
    timeoutMs = 20_000,
    context?: { interview_id: string; language?: string },
  ): Promise<Blob> => {
    if (!csrf) await getSession();
    const response = await fetch("/api/tts", {
      ...json({ text, ...context }),
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf!,
        "X-Requested-With": "interview-studio",
      },
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!response.ok)
      throw new ApiError(response.status, "Cloud speech unavailable");
    return response.blob();
  },
  practice: () => request<PracticeTask[]>("/practice"),
  completeTask: (id: string, completed: boolean) =>
    request<PracticeTask>(`/practice/${id}`, json({ completed }, "PATCH")),
  agentRuns: () => request<AgentRun[]>("/agent-runs"),
  billing: () => request<Billing>("/billing"),
  checkout: (plan: string) =>
    request<{ url: string }>("/billing/checkout", json({ plan })),
  portal: () => request<{ url: string }>("/billing/portal", { method: "POST" }),
};
export const VERDICT_LABEL: Record<Report["verdict"], string> = {
  insufficient_evidence: "More evidence needed",
  strong_hire: "Excellent evidence",
  hire: "Strong evidence",
  lean_hire: "Developing",
  no_hire: "Needs practice",
};
export function fmtDate(ts: number) {
  return new Date(ts * 1000).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
export function fmtClock(seconds: number) {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
