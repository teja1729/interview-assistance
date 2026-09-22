"""Google OIDC registration/sign-in, personal account discovery and logout."""

import logging

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..auth import COOKIE, Context, current_context, issue_session
from ..config import settings
from ..db import get_session
from ..models import LoginSession, Membership, User, Workspace

router = APIRouter(prefix="/api/auth", tags=["authentication"])
log = logging.getLogger(__name__)
oauth = OAuth()
oauth.register(
    "google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
)


def provision(session, sub, email, name, avatar="", demo=False):
    user = session.exec(select(User).where(User.google_sub == sub)).first()
    if not user:
        user = User(google_sub=sub, email=email, name=name, avatar_url=avatar)
        workspace = Workspace(
            name=name or "Personal account",
            plan="pro" if demo else "free",
        )
        session.add(user)
        session.add(workspace)
        session.flush()
        session.add(Membership(user_id=user.id, workspace_id=workspace.id, role="owner"))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            user = session.exec(select(User).where(User.google_sub == sub)).one()
    else:
        user.email, user.name, user.avatar_url = email, name, avatar
        session.add(user)
        session.commit()
    member = session.exec(
        select(Membership)
        .where(Membership.user_id == user.id, Membership.role == "owner")
        .order_by(Membership.created_at)
    ).first()
    if not member:
        raise HTTPException(403, "No personal account is available. Contact the application operator.")
    return user, session.get(Workspace, member.workspace_id)


@router.get("/config")
def config():
    return {"google_enabled": settings.google_enabled, "demo_enabled": settings.demo_login and not settings.production}


@router.get("/google")
async def google_login(request: Request):
    if not settings.google_enabled:
        raise HTTPException(503, "Google sign-in is not configured yet")
    target = request.query_params.get("next", "/dashboard")
    request.session["return_to"] = (
        target if target.startswith("/") and not target.startswith("//") and "\\" not in target else "/dashboard"
    )
    return await oauth.google.authorize_redirect(request, f"{settings.frontend_origin}/api/auth/google/callback")


@router.get("/google/callback")
async def google_callback(request: Request, session: Session = Depends(get_session)):
    try:
        # Authlib validates state, signature, issuer, audience, expiry and nonce via OIDC discovery.
        token = await oauth.google.authorize_access_token(request)
        identity = token.get("userinfo")
        if not identity or identity.get("email_verified") is not True or not identity.get("sub"):
            raise ValueError("A verified Google identity is required")
        user, workspace = provision(
            session,
            identity["sub"],
            identity["email"].lower(),
            identity.get("name", "Member"),
            identity.get("picture", ""),
        )
        target = request.session.get("return_to", "/dashboard")
        response = RedirectResponse(f"{settings.frontend_origin}{target}", status_code=303)
        issue_session(response, session, user, workspace)
        request.session.clear()  # OAuth access/refresh tokens are never retained.
        return response
    except Exception as exc:  # noqa: BLE001 - boundary logs only the exception class, never provider secrets
        session.rollback()
        log.warning("Google sign-in failed: %s", type(exc).__name__)
        request.session.clear()
        return RedirectResponse(f"{settings.frontend_origin}/login?error=google", status_code=303)


@router.post("/demo")
def demo_login(response: Response, session: Session = Depends(get_session)):
    if not settings.demo_login or settings.production:
        raise HTTPException(404, "Not found")
    user, workspace = provision(session, "development-demo", "demo@example.test", "Alex Morgan", demo=True)
    issue_session(response, session, user, workspace)
    return {"ok": True}


@router.get("/me")
def me(ctx: Context = Depends(current_context)):
    return {
        "user": ctx.user.model_dump(exclude={"google_sub"}),
        "account": {"id": ctx.workspace.id, "plan": ctx.workspace.plan},
        "csrf_token": ctx.login.csrf_token,
        "demo": ctx.user.google_sub == "development-demo",
    }


@router.post("/logout")
def logout(response: Response, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    session.delete(ctx.login)
    session.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.post("/logout-all")
def logout_all(response: Response, ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    for login in session.exec(select(LoginSession).where(LoginSession.user_id == ctx.user.id)).all():
        session.delete(login)
    session.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
