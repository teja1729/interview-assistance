"""Tenant-owned entities. Opaque IDs never replace workspace authorization.

JSON stores bounded agent artifacts; turns, memberships, jobs, usage and audit events
are relational. Use migrations for changes, never create_all in the application.
"""

import time
import uuid
from typing import Any

from sqlalchemy import JSON, Column, Integer, UniqueConstraint
from sqlmodel import Field, SQLModel


def uid() -> str:
    return uuid.uuid4().hex


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=uid, primary_key=True)
    google_sub: str = Field(unique=True, index=True)
    email: str = Field(index=True)
    name: str
    avatar_url: str = ""
    created_at: float = Field(default_factory=time.time)


class Workspace(SQLModel, table=True):
    """Historical table name for a personal account container; not a product workspace.

    Keep IDs and billing references stable. ai_profiles is a legacy, ignored preference;
    new routing comes from config/models.toml and interview-specific snapshots.
    """

    __tablename__ = "workspaces"
    id: str = Field(default_factory=uid, primary_key=True)
    name: str
    plan: str = "free"
    stripe_customer_id: str | None = Field(default=None, unique=True)
    stripe_subscription_id: str | None = None
    billing_status: str = "free"
    billing_event_at: int = 0
    billing_version: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    ai_profiles: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: float = Field(default_factory=time.time)


class Membership(SQLModel, table=True):
    __tablename__ = "memberships"
    workspace_id: str = Field(foreign_key="workspaces.id", primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    role: str = "member"
    created_at: float = Field(default_factory=time.time)


class LoginSession(SQLModel, table=True):
    __tablename__ = "login_sessions"
    token_hash: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    workspace_id: str = Field(foreign_key="workspaces.id")
    csrf_token: str
    expires_at: float = Field(index=True)


class Invitation(SQLModel, table=True):
    __tablename__ = "invitations"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    email: str
    token_hash: str = Field(unique=True)
    expires_at: float
    accepted_at: float | None = None


class Resume(SQLModel, table=True):
    __tablename__ = "resumes"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str
    filename: str
    mime: str
    candidate_name: str = ""
    summary: str = ""
    digest: str = ""
    # Original extracted text, never the model's digest. Older uploads require re-upload to share.
    extracted_text: str | None = None
    created_at: float = Field(default_factory=time.time)


class RecruiterProfile(SQLModel, table=True):
    __tablename__ = "recruiter_profiles"
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    company_name: str
    job_title: str = ""
    created_at: float = Field(default_factory=time.time)


class CandidateProfile(SQLModel, table=True):
    """Explicitly published fields only; private interview records are never directory data."""

    __tablename__ = "candidate_profiles"
    id: str = Field(default_factory=uid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", unique=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    display_name: str
    headline: str = ""
    target_role: str = ""
    location: str = ""
    experience_years: int = 0
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    discoverable: bool = Field(default=False, index=True)
    # Historical ID, deliberately not a FK: deletion revokes grants before removing the resume.
    resume_id: str | None = None
    version: int = 0
    updated_at: float = Field(default_factory=time.time)


class ResumeAccessRequest(SQLModel, table=True):
    __tablename__ = "resume_access_requests"
    __table_args__ = (UniqueConstraint("candidate_profile_id", "recruiter_user_id"),)
    id: str = Field(default_factory=uid, primary_key=True)
    candidate_profile_id: str = Field(foreign_key="candidate_profiles.id", index=True)
    recruiter_user_id: str = Field(foreign_key="users.id", index=True)
    resume_id: str
    # Snapshot the identity presented when consent was requested.
    recruiter_name: str
    recruiter_email: str
    company_name: str
    job_title: str = ""
    message: str = ""
    status: str = "pending"
    created_at: float = Field(default_factory=time.time)
    decided_at: float | None = None


class Interview(SQLModel, table=True):
    __tablename__ = "interviews"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    created_at: float = Field(default_factory=time.time, index=True)
    started_at: float | None = None
    ended_at: float | None = None
    status: str = "lobby"  # lobby, active, complete, finishing, finished, report_failed, abandoned
    version: int = 0
    lock_token: str | None = None
    lock_until: float = 0
    job_title: str
    company: str = ""
    experience_years: int = 0
    job_description: str = ""
    custom_instructions: str = ""
    duration_minutes: int = 30
    persona: str = "hiring_manager"
    resume_id: str | None = None  # historical reference; snapshot survives deletion
    resume_snapshot: str = ""
    plan: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    ai_profiles: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    current_topic: int = 0
    followup_count: int = 0
    closing_remark: str | None = None
    report: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    score: int | None = None


class Turn(SQLModel, table=True):
    __tablename__ = "turns"
    __table_args__ = (UniqueConstraint("interview_id", "position"),)
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    interview_id: str = Field(foreign_key="interviews.id", index=True)
    position: int
    topic: int = 0
    question: str
    answer: str | None = None
    assessment: str | None = None
    at: float = Field(default_factory=time.time)


class Operation(SQLModel, table=True):
    __tablename__ = "operations"
    __table_args__ = (UniqueConstraint("interview_id", "request_id"),)
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    interview_id: str = Field(foreign_key="interviews.id", index=True)
    request_id: str
    fingerprint: str
    response: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    interview_id: str | None = Field(default=None, index=True)
    agent: str
    prompt_version: str
    provider: str
    model: str
    status: str
    duration_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    error_code: str | None = None
    operation_id: str | None = None
    stage: str = "inference"
    attempt: int = 1
    created_at: float = Field(default_factory=time.time, index=True)


class AgentJob(SQLModel, table=True):
    __tablename__ = "agent_jobs"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(foreign_key="users.id")
    interview_id: str = Field(foreign_key="interviews.id", unique=True)
    status: str = Field(default="pending", index=True)
    attempts: int = 0
    lease_token: str | None = None
    lease_until: float = 0
    available_at: float = Field(default_factory=time.time)
    error: str | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: float = Field(default_factory=time.time)


class PromptBundle(SQLModel, table=True):
    """Global immutable operator prompts only; no candidate data or credentials."""

    __tablename__ = "prompt_bundles"
    id: str = Field(primary_key=True)
    prompts: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    created_at: float = Field(default_factory=time.time)


class CompanyResearch(SQLModel, table=True):
    """Candidate-owned cache: search queries never include resumes or interview answers."""

    __tablename__ = "company_research"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    cache_key: str = Field(index=True)
    data: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    expires_at: float
    created_at: float = Field(default_factory=time.time)


class SetupArtifact(SQLModel, table=True):
    """Persisted candidate-owned setup outputs. Refresh creates a new revision."""

    __tablename__ = "setup_artifacts"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    kind: str
    cache_key: str = Field(index=True)
    inputs: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    data: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    created_at: float = Field(default_factory=time.time)


class PracticeTask(SQLModel, table=True):
    __tablename__ = "practice_tasks"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    interview_id: str = Field(foreign_key="interviews.id", index=True)
    title: str
    instructions: str
    skill: str
    skill_id: str | None = None
    exercise_type: str | None = None
    active_key: str | None = Field(default=None, unique=True, index=True)
    minutes: int = 15
    completed_at: float | None = None
    created_at: float = Field(default_factory=time.time)


class PracticeTaskSource(SQLModel, table=True):
    """An interview can reinforce an existing unfinished exercise without duplicating it."""

    __tablename__ = "practice_task_sources"
    task_id: str = Field(foreign_key="practice_tasks.id", primary_key=True)
    interview_id: str = Field(foreign_key="interviews.id", primary_key=True)


class UsageBucket(SQLModel, table=True):
    __tablename__ = "usage_buckets"
    workspace_id: str = Field(foreign_key="workspaces.id", primary_key=True)
    period: str = Field(primary_key=True)
    resource: str = Field(primary_key=True)
    used: int = 0


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"
    id: str = Field(default_factory=uid, primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(foreign_key="users.id")
    action: str
    subject_id: str = ""
    created_at: float = Field(default_factory=time.time)


class BillingEvent(SQLModel, table=True):
    __tablename__ = "billing_events"
    id: str = Field(primary_key=True)
    created_at: float = Field(default_factory=time.time)
