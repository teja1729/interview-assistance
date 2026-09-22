"""Private resume library. Retain extracted text for consented sharing, never PDF binaries."""

import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from sqlmodel import Session, select

from ..agents.runtime import execute
from ..auth import Context, current_context
from ..db import get_session
from ..models import Resume
from ..schemas import ResumeDigest
from ..services.discovery import revoke_resume
from ..services.usage import consume, rate_limit

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


def owned(session, ctx, resume_id):
    item = session.get(Resume, resume_id)
    if not item or item.workspace_id != ctx.workspace.id or item.user_id != ctx.user.id:
        raise HTTPException(404, "Resume not found")
    return item


@router.get("")
def listing(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    items = session.exec(
        select(Resume)
        .where(Resume.workspace_id == ctx.workspace.id, Resume.user_id == ctx.user.id)
        .order_by(Resume.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            **r.model_dump(exclude={"digest", "workspace_id", "user_id", "extracted_text"}),
            "shareable": bool(r.extracted_text),
        }
        for r in items
    ]


@router.post("", status_code=201)
def upload(
    file: UploadFile = File(...),
    name: str = Form("", max_length=120),
    ctx: Context = Depends(current_context),
    session: Session = Depends(get_session),
):
    if file.content_type not in {"application/pdf", "text/plain", "text/markdown"}:
        raise HTTPException(400, "Upload a PDF or plain-text resume")
    raw = file.file.read(10 * 1024 * 1024 + 1)
    if not raw or len(raw) > 10 * 1024 * 1024:
        raise HTTPException(400, "Upload a non-empty resume under 10 MB")
    try:
        if file.content_type == "application/pdf":
            reader = PdfReader(io.BytesIO(raw))
            if reader.is_encrypted or len(reader.pages) > 30:
                raise ValueError("Encrypted or oversized PDF")
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        else:
            text = raw.decode("utf-8-sig")
    except Exception as exc:
        raise HTTPException(400, "The file could not be read. Use a text-based PDF or UTF-8 text file.") from exc
    if len(text.strip()) < 20:
        raise HTTPException(400, "No readable resume text found. Scanned PDFs need OCR before upload.")
    if len(text) > 60000:
        raise HTTPException(400, "Resume text is too long (60,000 character limit)")
    rate_limit(session, ctx.workspace)
    consume(session, ctx.workspace)
    digest = execute(
        "resume",
        {"text": text},
        ResumeDigest,
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        engine=session.bind,
    )
    resume = Resume(
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        name=name.strip() or (file.filename or "Resume")[:120],
        filename=(file.filename or "resume")[:255],
        mime=file.content_type,
        extracted_text=text,
        **digest.model_dump(),
    )
    session.add(resume)
    session.commit()
    return {**resume.model_dump(exclude={"digest", "workspace_id", "user_id", "extracted_text"}), "shareable": True}


@router.get("/{resume_id}")
def detail(resume_id: str, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    return owned(session, ctx, resume_id).model_dump(exclude={"workspace_id", "user_id", "extracted_text"})


@router.delete("/{resume_id}")
def delete(resume_id: str, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    item = owned(session, ctx, resume_id)
    revoke_resume(session, ctx, resume_id)
    session.delete(item)
    session.commit()
    return {"ok": True}
