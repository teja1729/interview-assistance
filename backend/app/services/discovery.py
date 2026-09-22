"""Consent boundary for recruiters. Never join interviews, scores or agent artifacts here.

Mutations serialize on the candidate profile (UPDATE works on SQLite and PostgreSQL),
then re-read consent. Requests pin a resume and recruiter identity. Changing the resume,
withdrawing visibility, or deleting an upload revokes grants in the same transaction.
Only the candidate can approve; every shared read rechecks all conditions.
"""

import time

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from ..models import CandidateProfile, Membership, RecruiterProfile, Resume, ResumeAccessRequest, User


def recruiter(session, ctx):
    profile = session.get(RecruiterProfile, ctx.user.id)
    if not profile:
        raise HTTPException(403, "Complete your recruiter profile first")
    return profile


def candidate(session, ctx):
    return session.exec(
        select(CandidateProfile).where(
            CandidateProfile.user_id == ctx.user.id, CandidateProfile.workspace_id == ctx.workspace.id
        )
    ).first()


def lock_profile(session, profile_id):
    result = session.execute(
        update(CandidateProfile).where(CandidateProfile.id == profile_id).values(version=CandidateProfile.version + 1)
    )
    if result.rowcount != 1:
        raise HTTPException(404, "Candidate not found")
    session.expire_all()
    return session.get(CandidateProfile, profile_id)


def revoke(session, profile):
    session.execute(
        update(ResumeAccessRequest)
        .where(
            ResumeAccessRequest.candidate_profile_id == profile.id,
            ResumeAccessRequest.status.in_(["pending", "approved"]),
        )
        .values(status="revoked", decided_at=time.time())
    )


def revoke_resume(session, ctx, resume_id):
    profile = candidate(session, ctx)
    if profile and profile.resume_id == resume_id:
        profile = lock_profile(session, profile.id)
        if profile.resume_id != resume_id:
            return
        revoke(session, profile)
        profile.resume_id = None
        profile.discoverable = False
        profile.updated_at = time.time()
        session.add(profile)


def save_candidate(session, ctx, body):
    profile = candidate(session, ctx)
    if profile:
        profile = lock_profile(session, profile.id)
    else:
        profile = CandidateProfile(user_id=ctx.user.id, workspace_id=ctx.workspace.id, display_name=ctx.user.name)
    if body.resume_id:
        resume = session.get(Resume, body.resume_id)
        if not resume or resume.user_id != ctx.user.id or resume.workspace_id != ctx.workspace.id:
            raise HTTPException(404, "Resume not found")
        if not resume.extracted_text:
            raise HTTPException(422, "Re-upload this resume to enable sharing its original text")
    if body.discoverable and (not body.resume_id or not body.target_role.strip()):
        raise HTTPException(422, "Choose a resume and target role before publishing")
    if profile.resume_id != body.resume_id or not body.discoverable:
        revoke(session, profile)
    for key, value in body.model_dump().items():
        setattr(profile, key, value.strip() if isinstance(value, str) else value)
    profile.updated_at = time.time()
    session.add(profile)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Profile changed in another tab. Refresh and try again.") from exc
    return profile


def available_resume(session, profile):
    if not profile or not profile.discoverable:
        raise HTTPException(404, "Candidate is no longer available")
    member = session.get(Membership, (profile.workspace_id, profile.user_id))
    resume = session.get(Resume, profile.resume_id) if profile.resume_id else None
    if (
        not member
        or not resume
        or resume.user_id != profile.user_id
        or resume.workspace_id != profile.workspace_id
        or not resume.extracted_text
    ):
        raise HTTPException(404, "Shared resume is no longer available")
    return resume


def public_profile(profile):
    return profile.model_dump(
        include={
            "id",
            "display_name",
            "headline",
            "target_role",
            "location",
            "experience_years",
            "skills",
            "updated_at",
        }
    )


def request_access(session, ctx, profile_id, message):
    company = recruiter(session, ctx)
    company_name, job_title = company.company_name, company.job_title
    profile = lock_profile(session, profile_id)
    resume = available_resume(session, profile)
    if profile.user_id == ctx.user.id:
        raise HTTPException(400, "You cannot request your own resume")
    request = session.exec(
        select(ResumeAccessRequest).where(
            ResumeAccessRequest.candidate_profile_id == profile.id,
            ResumeAccessRequest.recruiter_user_id == ctx.user.id,
        )
    ).first()
    if request and request.status != "revoked":
        session.commit()
        return request  # Repeated clicks cannot reset a candidate's decision.
    if not request:
        request = ResumeAccessRequest(
            candidate_profile_id=profile.id,
            recruiter_user_id=ctx.user.id,
            resume_id=resume.id,
            recruiter_name=ctx.user.name,
            recruiter_email=ctx.user.email,
            company_name=company_name,
        )
    request.resume_id = resume.id
    request.recruiter_name, request.recruiter_email = ctx.user.name, ctx.user.email
    request.company_name, request.job_title = company_name, job_title
    request.message, request.status = message.strip(), "pending"
    request.created_at, request.decided_at = time.time(), None
    session.add(request)
    session.commit()
    return request


def decide(session, ctx, request_id, status):
    request = session.get(ResumeAccessRequest, request_id)
    if not request:
        raise HTTPException(404, "Request not found")
    profile = session.get(CandidateProfile, request.candidate_profile_id)
    if profile.user_id != ctx.user.id or profile.workspace_id != ctx.workspace.id:
        raise HTTPException(404, "Request not found")
    profile = lock_profile(session, profile.id)
    session.refresh(request)
    if request.status == status:
        session.commit()
        return request
    if status == "revoked":
        if request.status not in {"approved", "pending"}:
            raise HTTPException(409, "This request is already closed")
    elif request.status != "pending":
        raise HTTPException(409, "Only pending requests can be approved or declined")
    if status == "approved" and available_resume(session, profile).id != request.resume_id:
        raise HTTPException(409, "The selected resume changed. Ask for a new request.")
    request.status, request.decided_at = status, time.time()
    session.add(request)
    session.commit()
    return request


def shared_resume(session, ctx, request_id):
    recruiter(session, ctx)
    request = session.get(ResumeAccessRequest, request_id)
    if not request or request.recruiter_user_id != ctx.user.id:
        raise HTTPException(404, "Request not found")
    if request.status != "approved":
        raise HTTPException(403, "The candidate has not approved access")
    profile = session.get(CandidateProfile, request.candidate_profile_id)
    resume = available_resume(session, profile)
    if resume.id != request.resume_id:
        raise HTTPException(403, "Access to this resume has expired")
    user = session.get(User, profile.user_id)
    return {
        "candidate_name": profile.display_name,
        "email": user.email,
        "resume_name": resume.name,
        "text": resume.extracted_text,
    }
