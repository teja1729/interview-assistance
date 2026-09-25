"""Google and LinkedIn OIDC sign-in, personal account discovery and logout."""

import logging

import httpx
from authlib.integrations.base_client.errors import MismatchingStateError, OAuthError
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
oauth.register(
    "linkedin",
    client_id=settings.linkedin_client_id,
    client_secret=settings.linkedin_client_secret,
    server_metadata_url="https://www.linkedin.com/oauth/.well-known/openid-configuration",
    # LinkedIn rejects HTTP Basic client authentication on the token endpoint.
    client_kwargs={
        "scope": "openid profile email",
        "token_endpoint_auth_method": "client_secret_post",
    },
)


def provision(session, sub, email, name, avatar="", demo=False, provider="google"):
    if provider not in {"google", "linkedin"}:
        raise HTTPException(400, "Unsupported sign-in provider")
    user = session.exec(select(User).where(User.auth_provider == provider, User.google_sub == sub)).first()
    if not user:
        user = User(auth_provider=provider, google_sub=sub, email=email, name=name, avatar_url=avatar)
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
            user = session.exec(select(User).where(User.auth_provider == provider, User.google_sub == sub)).one()
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


def _safe_next(value: str, default: str = "/dashboard") -> str:
    if value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return default


def _failure_page(request: Request) -> str:
    target = request.session.get("return_to", "/dashboard")
    return "/recruiter/login" if str(target).startswith("/recruiter") else "/login"


@router.get("/config")
def config():
    return {
        "google_enabled": settings.google_enabled,
        "linkedin_enabled": settings.linkedin_enabled,
        "demo_enabled": settings.demo_login and not settings.production,
    }


@router.get("/google")
async def google_login(request: Request):
    if not settings.google_enabled:
        raise HTTPException(503, "Google sign-in is not configured yet")
    request.session["return_to"] = _safe_next(request.query_params.get("next", "/dashboard"))
    return await oauth.google.authorize_redirect(request, f"{settings.frontend_origin}/api/auth/google/callback")


@router.get("/linkedin")
async def linkedin_login(request: Request):
    if not settings.linkedin_enabled:
        raise HTTPException(503, "LinkedIn sign-in is not configured yet")
    request.session["return_to"] = _safe_next(request.query_params.get("next", "/dashboard"))
    return await oauth.linkedin.authorize_redirect(request, f"{settings.frontend_origin}/api/auth/linkedin/callback")


async def _linkedin_identity(request: Request) -> dict:
    """Exchange the code with form fields. LinkedIn rejects Authlib's token request."""
    if request.query_params.get("error"):
        raise OAuthError(
            error=request.query_params.get("error"),
            description=request.query_params.get("error_description"),
        )
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    state_data = await oauth.linkedin.framework.get_state_data(request.session, state)
    await oauth.linkedin.framework.clear_state_data(request.session, state)
    if not state_data or not code:
        raise MismatchingStateError()
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": state_data.get("redirect_uri"),
        "client_id": settings.linkedin_client_id,
        "client_secret": settings.linkedin_client_secret,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        token_response = await client.post("https://www.linkedin.com/oauth/v2/accessToken", data=form)
        payload = token_response.json()
        if token_response.status_code >= 400 or payload.get("error"):
            raise OAuthError(
                error=payload.get("error") or "invalid_client", description=payload.get("error_description")
            )
        profile = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {payload['access_token']}"},
        )
        profile.raise_for_status()
        identity = profile.json()
    # LinkedIn only returns an email address after the member grants the email scope.
    if identity.get("email_verified") is None and identity.get("email"):
        identity["email_verified"] = True
    return identity


async def _finish_oidc(request: Request, session: Session, provider: str, client):
    try:
        if provider == "linkedin":
            identity = await _linkedin_identity(request)
        else:
            # Authlib validates state, signature, issuer, audience, expiry and nonce via OIDC discovery.
            token = await client.authorize_access_token(request)
            identity = token.get("userinfo") or {}
        if identity.get("email_verified") is not True or not identity.get("sub") or not identity.get("email"):
            raise ValueError("A verified identity is required")
        user, workspace = provision(
            session,
            identity["sub"],
            identity["email"].lower(),
            identity.get("name") or "Member",
            identity.get("picture") or "",
            provider=provider,
        )
        target = _safe_next(str(request.session.get("return_to", "/dashboard")))
        response = RedirectResponse(f"{settings.frontend_origin}{target}", status_code=303)
        issue_session(response, session, user, workspace)
        request.session.clear()  # OAuth access/refresh tokens are never retained.
        return response
    except Exception as exc:  # noqa: BLE001 - boundary logs only the exception class, never provider secrets
        session.rollback()
        detail = getattr(exc, "error", None) or type(exc).__name__
        description = getattr(exc, "description", None)
        if isinstance(description, str) and "secret" not in description.lower() and len(description) < 180:
            detail = f"{detail}: {description}"
        log.warning("%s sign-in failed: %s", provider, detail)
        page = _failure_page(request)
        request.session.clear()
        return RedirectResponse(f"{settings.frontend_origin}{page}?error={provider}", status_code=303)


@router.get("/google/callback")
async def google_callback(request: Request, session: Session = Depends(get_session)):
    return await _finish_oidc(request, session, "google", oauth.google)


@router.get("/linkedin/callback")
async def linkedin_callback(request: Request, session: Session = Depends(get_session)):
    return await _finish_oidc(request, session, "linkedin", oauth.linkedin)


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
        "user": ctx.user.model_dump(exclude={"google_sub", "auth_provider"}),
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
