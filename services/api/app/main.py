from contextlib import asynccontextmanager
from datetime import UTC
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import config
from app.codes import generate_code, is_valid_alias
from app.db import create_schema, engine, get_session
from app.models import Link, utcnow
from app.schemas import LinkCreate, LinkOut

MAX_CODE_ATTEMPTS = 5

# One database session per request, injected by FastAPI.
SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates tables on startup. Replaced by Alembic migrations later, so
    # schema changes are versioned and reviewed like code.
    create_schema(engine)
    yield


app = FastAPI(title="LinkPulse API", lifespan=lifespan)


def to_out(link: Link) -> LinkOut:
    return LinkOut(
        code=link.code,
        short_url=f"{config.BASE_URL}/{link.code}",
        target_url=link.target_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


@app.get("/healthz")
def healthz() -> dict:
    """Liveness: the process is up. Never checks dependencies, or a database
    outage would make Kubernetes restart every healthy API pod. Also reports
    the build, so you can check which commit a pod is running."""
    return {"status": "ok", "version": config.VERSION}


@app.get("/readyz")
def readyz(session: SessionDep) -> dict:
    """Readiness: can this pod serve traffic right now? Kubernetes stops
    routing requests to the pod while this fails."""
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable") from None
    return {"status": "ready"}


@app.post("/links", status_code=status.HTTP_201_CREATED, response_model=LinkOut)
def create_link(body: LinkCreate, session: SessionDep) -> LinkOut:
    expires_at = body.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= utcnow():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "expires_at must be in the future")

    if body.alias is not None:
        if not is_valid_alias(body.alias):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "alias must be 3-32 letters, digits, '-' or '_', and not a reserved word",
            )
        if session.get(Link, body.alias) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "alias already in use")
        code = body.alias
    else:
        # Random codes can collide; retry a few times before giving up.
        for _ in range(MAX_CODE_ATTEMPTS):
            code = generate_code(config.CODE_LENGTH)
            if session.get(Link, code) is None:
                break
        else:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "could not allocate a short code")

    link = Link(code=code, target_url=str(body.url), expires_at=expires_at)
    session.add(link)
    session.commit()
    return to_out(link)


@app.get("/links/{code}", response_model=LinkOut)
def get_link(code: str, session: SessionDep) -> LinkOut:
    link = session.get(Link, code)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "link not found")
    return to_out(link)


@app.get("/{code}")
def redirect(code: str, session: SessionDep) -> RedirectResponse:
    link = session.get(Link, code)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "link not found")
    if link.is_expired(utcnow()):
        raise HTTPException(status.HTTP_410_GONE, "link has expired")
    # 302, not 301: browsers cache 301 redirects and would skip us on repeat
    # visits, so those clicks would never be counted.
    return RedirectResponse(link.target_url, status_code=status.HTTP_302_FOUND)
