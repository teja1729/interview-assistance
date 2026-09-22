"""Isolated identities and databases. Tests never use developer data or paid models."""

import os
import secrets
import time

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

os.environ["AI_DEFAULT_PROFILE"] = "demo"
os.environ["AUTH_DEMO_ENABLED"] = "true"
os.environ["INLINE_WORKER"] = "false"
os.environ["APP_ENV"] = "development"
os.environ["AUDIO_PROVIDER"] = "browser"
os.environ["LOCAL_USAGE_OVERRIDES"] = "false"

from app import db
from app.auth import COOKIE, token_hash
from app.main import app
from app.models import LoginSession, Membership, User, Workspace


@pytest.fixture
def engine(tmp_path):
    url = os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    engine = db.make_engine(url)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def clients(engine):
    def get_session():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[db.get_session] = get_session
    opened = []

    def create(email="alex@example.test", plan="free", role="owner"):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with Session(engine, expire_on_commit=False) as session:
            user = User(google_sub=secrets.token_hex(16), email=email, name=email.split("@")[0])
            workspace = Workspace(name="Test workspace", plan=plan)
            session.add(user)
            session.add(workspace)
            session.flush()
            session.add(Membership(user_id=user.id, workspace_id=workspace.id, role=role))
            session.add(
                LoginSession(
                    token_hash=token_hash(token),
                    user_id=user.id,
                    workspace_id=workspace.id,
                    csrf_token=csrf,
                    expires_at=time.time() + 3600,
                )
            )
            session.commit()
        client = TestClient(app, headers={"X-Requested-With": "interview-studio", "X-CSRF-Token": csrf})
        client.cookies.set(COOKIE, token)
        client.user_id, client.workspace_id = user.id, workspace.id
        opened.append(client)
        return client

    yield create
    for client in opened:
        client.close()
    app.dependency_overrides.clear()
