"""Thin HTTP boundary. Interview business rules live in services/interviews.py."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from ..auth import Context, current_context
from ..db import get_session
from ..models import Interview
from ..schemas import InterviewCreate, TextTurn
from ..services import interviews as service

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


@router.get("")
def history(
    ctx: Context = Depends(current_context), session: Session = Depends(get_session), limit: int = 100, offset: int = 0
):
    query = select(Interview).where(Interview.workspace_id == ctx.workspace.id, Interview.user_id == ctx.user.id)
    items = session.exec(
        query.order_by(Interview.created_at.desc()).offset(max(0, offset)).limit(min(100, max(1, limit)))
    ).all()
    return [
        {
            "id": iv.id,
            "created_at": iv.created_at,
            "ended_at": iv.ended_at,
            "status": iv.status,
            "job_title": iv.job_title,
            "company": iv.company,
            "persona": iv.persona,
            "duration_minutes": iv.duration_minutes,
            "score": iv.score,
            "user_id": iv.user_id,
            "verdict": (iv.report or {}).get("verdict"),
            "turns": sum(bool(t.answer) for t in service.turns_for(session, iv)),
        }
        for iv in items
    ]


@router.post("", status_code=201)
def create(body: InterviewCreate, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return service.create(session, ctx, body)


@router.get("/{interview_id}")
def detail(interview_id: str, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return service.public(session, service.get_interview(session, ctx, interview_id))


@router.post("/{interview_id}/join")
def join(interview_id: str, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return service.join(session, ctx, interview_id)


@router.post("/{interview_id}/turn-text")
def turn_text(
    interview_id: str, body: TextTurn, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    if not body.text.strip():
        raise HTTPException(400, "An answer is required")
    return service.apply_turn(session, ctx, interview_id, body.version, body.request_id, answer=body.text)


@router.post("/{interview_id}/turn")
def turn_audio(
    interview_id: str,
    audio: UploadFile = File(...),
    version: int = Form(ge=0),
    request_id: str = Form(min_length=16, max_length=80),
    ctx: Context = Depends(current_context),
    session: Session = Depends(get_session),
):
    raw = audio.file.read(10 * 1024 * 1024 + 1)
    if not 1000 <= len(raw) <= 10 * 1024 * 1024:
        raise HTTPException(400, "Recording must be between one second and five minutes")
    return service.apply_turn(session, ctx, interview_id, version, request_id, audio=raw)


@router.post("/{interview_id}/finish")
def finish(interview_id: str, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return service.finish(session, ctx, interview_id)


@router.post("/{interview_id}/abandon")
def abandon(interview_id: str, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return service.abandon(session, ctx, interview_id)
