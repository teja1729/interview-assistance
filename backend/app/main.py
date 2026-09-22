"""Application composition. Keep domain behavior in services and HTTP contracts in api/."""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .api import auth, billing, discovery, interviews, meta, practice, progress, resumes
from .config import settings
from .providers.base import ProviderError
from .services.reports import process_one

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")


async def worker_loop():
    while True:
        try:
            await asyncio.to_thread(process_one)
        except Exception as exc:  # noqa: BLE001 - boundary logs only the exception class, never provider secrets
            log.error("inline_worker error=%s", type(exc).__name__)
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app):
    settings.validate()
    task = asyncio.create_task(worker_loop()) if settings.inline_worker else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Interview Studio API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.production else "/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="oauth_state",
    https_only=settings.production,
    same_site="lax",
    max_age=600,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Requested-With"],
)


@app.middleware("http")
async def request_boundary(request: Request, call_next):
    request_id = uuid.uuid4().hex
    started = time.monotonic()
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path != "/api/billing/webhook":
        origin = request.headers.get("origin")
        if (origin and origin != settings.frontend_origin) or (
            not origin and request.headers.get("x-requested-with") != "interview-studio"
        ):
            return JSONResponse({"detail": "Untrusted request origin"}, status_code=403)
    # Bound request size before multipart processing. The reverse proxy also enforces this limit.
    try:
        too_large = int(request.headers.get("content-length", "0")) > 12 * 1024 * 1024
    except ValueError:
        return JSONResponse({"detail": "Invalid content length"}, status_code=400)
    if too_large:
        return JSONResponse({"detail": "Request too large"}, status_code=413)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    log.info(
        "request=%s method=%s path=%s status=%s duration_ms=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.monotonic() - started) * 1000,
    )
    return response


@app.exception_handler(ProviderError)
async def provider_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


for router in (
    auth.router,
    interviews.router,
    resumes.router,
    discovery.router,
    progress.router,
    practice.router,
    billing.router,
    meta.router,
):
    app.include_router(router)
