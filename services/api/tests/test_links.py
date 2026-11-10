from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app


@pytest.fixture
def client():
    # Fresh in-memory database per test, so tests never affect each other.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_create_and_redirect(client):
    resp = client.post("/links", json={"url": "https://example.com/page"})
    assert resp.status_code == 201
    code = resp.json()["code"]
    assert len(code) == 7

    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/page"


def test_custom_alias(client):
    resp = client.post("/links", json={"url": "https://example.com", "alias": "my-link"})
    assert resp.status_code == 201
    assert resp.json()["short_url"].endswith("/my-link")


def test_duplicate_alias_conflicts(client):
    client.post("/links", json={"url": "https://example.com", "alias": "taken"})
    resp = client.post("/links", json={"url": "https://example.org", "alias": "taken"})
    assert resp.status_code == 409


@pytest.mark.parametrize("alias", ["ab", "has space", "healthz", "x" * 33])
def test_invalid_alias_rejected(client, alias):
    resp = client.post("/links", json={"url": "https://example.com", "alias": alias})
    assert resp.status_code == 422


def test_invalid_url_rejected(client):
    resp = client.post("/links", json={"url": "not-a-url"})
    assert resp.status_code == 422


def test_unknown_code_returns_404(client):
    assert client.get("/nope123", follow_redirects=False).status_code == 404


def test_expired_link_returns_410(client, monkeypatch):
    expiry = datetime.now(UTC) + timedelta(hours=1)
    resp = client.post(
        "/links", json={"url": "https://example.com", "alias": "soon", "expires_at": expiry.isoformat()}
    )
    assert resp.status_code == 201

    # Move the API's clock two hours ahead instead of sleeping in the test.
    monkeypatch.setattr("app.main.utcnow", lambda: expiry + timedelta(hours=1))
    assert client.get("/soon", follow_redirects=False).status_code == 410


def test_past_expiry_rejected(client):
    past = datetime.now(UTC) - timedelta(minutes=1)
    resp = client.post("/links", json={"url": "https://example.com", "expires_at": past.isoformat()})
    assert resp.status_code == 422
