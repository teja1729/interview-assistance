"""Authenticated recruiter directory and candidate-controlled consent endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import func, or_
from sqlmodel import Session, select

from ..auth import Context, current_context
from ..db import get_session
from ..models import CandidateProfile, Membership, RecruiterProfile, Resume, ResumeAccessRequest
from ..schemas import Contract
from ..services import discovery
from ..services.usage import rate_limit

router = APIRouter(prefix="/api", tags=["recruiting"])


class RecruiterInput(Contract):
    company_name: str = Field(min_length=2, max_length=150, pattern=r"\S")
    job_title: str = Field(default="", max_length=150)


class CandidateInput(Contract):
    display_name: str = Field(min_length=2, max_length=120, pattern=r"\S")
    headline: str = Field(default="", max_length=240)
    target_role: str = Field(default="", max_length=150)
    location: str = Field(default="", max_length=120)
    experience_years: int = Field(default=0, ge=0, le=50)
    skills: list[Annotated[str, Field(min_length=1, max_length=60, pattern=r"\S")]] = Field(
        default_factory=list, max_length=20
    )
    discoverable: bool = False
    resume_id: str | None = Field(default=None, max_length=64)


class AccessInput(Contract):
    message: str = Field(min_length=10, max_length=1500, pattern=r"\S")


class DecisionInput(Contract):
    status: Literal["approved", "denied", "revoked"]


@router.get("/recruiter/profile")
def recruiter_profile(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    profile = session.get(RecruiterProfile, ctx.user.id)
    return profile.model_dump(exclude={"user_id"}) if profile else None


@router.put("/recruiter/profile")
def save_recruiter(
    body: RecruiterInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    profile = session.get(RecruiterProfile, ctx.user.id) or RecruiterProfile(user_id=ctx.user.id, company_name="")
    profile.company_name, profile.job_title = body.company_name.strip(), body.job_title.strip()
    session.add(profile)
    session.commit()
    return profile.model_dump(exclude={"user_id"})


@router.get("/candidate-profile")
def candidate_profile(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    profile = discovery.candidate(session, ctx)
    return profile.model_dump(exclude={"user_id", "workspace_id", "version"}) if profile else None


@router.put("/candidate-profile")
def save_candidate(
    body: CandidateInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    return discovery.save_candidate(session, ctx, body).model_dump(exclude={"user_id", "workspace_id", "version"})


@router.get("/recruiter/candidates")
def candidates(
    q: str = Query("", max_length=150),
    min_experience: int = Query(0, ge=0, le=50),
    offset: int = Query(0, ge=0, le=100000),
    limit: int = Query(20, ge=1, le=50),
    ctx: Context = Depends(current_context),
    session: Session = Depends(get_session),
):
    discovery.recruiter(session, ctx)
    stmt = (
        select(CandidateProfile)
        .join(Resume, CandidateProfile.resume_id == Resume.id)
        .join(
            Membership,
            (Membership.user_id == CandidateProfile.user_id)
            & (Membership.workspace_id == CandidateProfile.workspace_id),
        )
        .where(
            CandidateProfile.discoverable == True,
            CandidateProfile.user_id != ctx.user.id,
            CandidateProfile.experience_years >= min_experience,
            Resume.user_id == CandidateProfile.user_id,
            Resume.workspace_id == CandidateProfile.workspace_id,
            Resume.extracted_text.is_not(None),
        )
    )
    if q.strip():
        term = q.strip().lower()
        stmt = stmt.where(
            or_(
                func.lower(CandidateProfile.target_role).contains(term, autoescape=True),
                func.lower(CandidateProfile.headline).contains(term, autoescape=True),
                func.lower(CandidateProfile.location).contains(term, autoescape=True),
            )
        )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(
        stmt.order_by(CandidateProfile.updated_at.desc(), CandidateProfile.id).offset(offset).limit(limit)
    ).all()
    return {"items": [discovery.public_profile(p) for p in items], "total": total}


@router.post("/recruiter/candidates/{profile_id}/request")
def request_access(
    profile_id: str, body: AccessInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    rate_limit(session, ctx.workspace)
    return discovery.request_access(session, ctx, profile_id, body.message).model_dump(
        exclude={"recruiter_user_id", "resume_id"}
    )


@router.get("/recruiter/requests")
def recruiter_requests(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    discovery.recruiter(session, ctx)
    rows = session.exec(
        select(ResumeAccessRequest, CandidateProfile.display_name)
        .join(CandidateProfile)
        .where(ResumeAccessRequest.recruiter_user_id == ctx.user.id)
        .order_by(ResumeAccessRequest.created_at.desc())
        .limit(200)
    ).all()
    return [{**r.model_dump(exclude={"recruiter_user_id", "resume_id"}), "candidate_name": name} for r, name in rows]


@router.get("/candidate-requests")
def candidate_requests(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    rows = session.exec(
        select(ResumeAccessRequest)
        .join(CandidateProfile)
        .where(CandidateProfile.user_id == ctx.user.id, CandidateProfile.workspace_id == ctx.workspace.id)
        .order_by(ResumeAccessRequest.created_at.desc())
        .limit(200)
    ).all()
    return [r.model_dump(exclude={"recruiter_user_id", "resume_id"}) for r in rows]


@router.patch("/candidate-requests/{request_id}")
def decide(
    request_id: str,
    body: DecisionInput,
    ctx: Context = Depends(current_context),
    session: Session = Depends(get_session),
):
    return discovery.decide(session, ctx, request_id, body.status).model_dump(
        exclude={"recruiter_user_id", "resume_id"}
    )


@router.get("/recruiter/requests/{request_id}/resume")
def shared_resume(request_id: str, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return discovery.shared_resume(session, ctx, request_id)
