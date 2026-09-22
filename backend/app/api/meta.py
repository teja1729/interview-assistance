"""Health, setup helpers and speech. Paid actions require authentication and usage reservation."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlmodel import Session

from ..agents.context import brief_for
from ..agents.runtime import execute
from ..auth import Context, current_context
from ..db import get_session
from ..personas import persona_list
from ..schemas import CompanyResearchInput, Language, Titles, public_company_url
from ..services import company_research, interviews, job_descriptions, setup_cache, speech
from ..services.usage import consume, rate_limit

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health():
    return {"ok": True, "service": "interview-studio", "version": "1.0.0"}


@router.get("/ready")
def ready(session: Session = Depends(get_session)):
    session.execute(text("SELECT 1"))
    session.execute(text("SELECT version_num FROM alembic_version"))
    return {"ok": True}


@router.get("/personas")
def personas(ctx: Context = Depends(current_context)):
    return persona_list()


@router.get("/capabilities")
def capabilities(ctx: Context = Depends(current_context)):
    return {
        "voice_input": speech.available(),
        "cloud_voice": speech.available(),
    }


class SuggestInput(BaseModel):
    job_title: str = Field(min_length=2, max_length=150)
    company: str = Field(default="", max_length=150)
    experience_years: int = Field(default=0, ge=0, le=50)
    company_url: str = Field(default="", max_length=2000)
    company_research_id: str | None = None
    force_refresh: bool = False
    _url = field_validator("company_url")(public_company_url)


@router.post("/company-research")
def research_company(
    body: CompanyResearchInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    identifier, brief = company_research.research(session, ctx, **body.model_dump())
    return {"id": identifier, **brief.model_dump()}


def helper(session, ctx, payload, schema):
    rate_limit(session, ctx.workspace)
    consume(session, ctx.workspace)
    return execute(
        "assistant",
        payload,
        schema,
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        engine=session.bind,
    ).model_dump()


@router.post("/suggest/titles")
def titles(body: SuggestInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    inputs = {"job_title": body.job_title.strip()}
    if not body.force_refresh and (saved := setup_cache.lookup(session, ctx, "titles", inputs)):
        return saved.data
    data = helper(session, ctx, inputs, Titles)
    data["titles"] = list(dict.fromkeys(t for t in data["titles"] if t.lower() != body.job_title.lower()))
    setup_cache.save(session, ctx, "titles", inputs, data)
    return data


@router.get("/setup/job-descriptions")
def saved_descriptions(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return setup_cache.list_drafts(session, ctx)


@router.get("/setup/job-descriptions/{identifier}")
def saved_description(
    identifier: str, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    return setup_cache.get(session, ctx, identifier)


@router.post("/suggest/job-description")
def job_description(
    body: SuggestInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    return job_descriptions.generate(session, ctx, body.model_dump())


class SpeechInput(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    interview_id: str | None = None
    language: Language | None = None


@router.post("/tts")
def tts(body: SpeechInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    language = body.language
    if body.interview_id:
        language = brief_for(interviews.get_interview(session, ctx, body.interview_id)).language
    rate_limit(session, ctx.workspace)
    consume(session, ctx.workspace)
    return Response(content=speech.synthesize(body.text, language), media_type="audio/wav")
