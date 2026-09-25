"""Opaque database sessions, CSRF protection and tenant context.

OAuth is only an identity bootstrap. Application authorization always derives from the
current database membership, never from email domains or client-provided workspace IDs.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from .config import settings
from .db import get_session
from .models import LoginSession, Membership, User, Workspace

COOKIE = "interview_session"
SESSION_SECONDS = 30 * 24 * 3600


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass
class Context:
    user: User
    workspace: Workspace
    membership: Membership
    login: LoginSession

    def require_owner(self):
        if self.membership.role != "owner":
            raise HTTPException(403, "Only the account owner can perform this action")


def current_context(request: Request, session: Session = Depends(get_session)) -> Context:
    token = request.cookies.get(COOKIE, "")
    login = session.get(LoginSession, token_hash(token)) if token else None
    if not login or login.expires_at <= time.time():
        raise HTTPException(401, "Sign in to continue")
    user = session.get(User, login.user_id)
    workspace = session.get(Workspace, login.workspace_id)
    membership = session.get(Membership, (login.workspace_id, login.user_id))
    if not user or not workspace or not membership:
        raise HTTPException(401, "This account is no longer available. Sign in again.")
    if user.google_sub == "development-demo" and (not settings.demo_login or settings.production):
        raise HTTPException(401, "Sign in to continue")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not secrets.compare_digest(
        request.headers.get("x-csrf-token", ""), login.csrf_token
    ):
        raise HTTPException(403, "Invalid CSRF token. Refresh the page and try again.")
    return Context(user, workspace, membership, login)


def issue_session(response, session: Session, user: User, workspace: Workspace):
    token = secrets.token_urlsafe(48)
    login = LoginSession(
        token_hash=token_hash(token),
        user_id=user.id,
        workspace_id=workspace.id,
        csrf_token=secrets.token_urlsafe(32),
        expires_at=time.time() + SESSION_SECONDS,
    )
    session.add(login)
    session.commit()
    response.set_cookie(
        COOKIE, token, max_age=SESSION_SECONDS, httponly=True, secure=settings.production, samesite="lax", path="/"
    )
    return login
