"""Create isolated browser-test identities; never imported by the application.

Only accepts an explicit /tmp SQLite database. The test backend must already be migrated.
Prints short-lived test cookies to its parent test process, never real account credentials.
"""

import json
import os
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session

from app.auth import token_hash
from app.db import make_engine
from app.models import LoginSession, Membership, User, Workspace

url = os.environ.get("RECRUITER_E2E_DATABASE_URL", "")
if not url.startswith("sqlite:////tmp/suri-browser-tests-"):
    raise SystemExit("Use an explicit isolated sqlite:////tmp/suri-browser-tests-... database")

identities = {}
with Session(make_engine(url)) as session:
    for role in ("candidate", "recruiter", "stranger"):
        tag = secrets.token_hex(5)
        user = User(google_sub=f"e2e-{tag}", email=f"{role}-{tag}@example.test", name=f"Test {role.title()}")
        workspace = Workspace(name="Isolated browser test", plan="pro")
        session.add(user)
        session.add(workspace)
        session.flush()
        session.add(Membership(user_id=user.id, workspace_id=workspace.id, role="owner"))
        token = secrets.token_urlsafe(32)
        session.add(
            LoginSession(
                token_hash=token_hash(token),
                user_id=user.id,
                workspace_id=workspace.id,
                csrf_token=secrets.token_urlsafe(32),
                expires_at=time.time() + 3600,
            )
        )
        identities[role] = {"token": token, "email": user.email}
    session.commit()
print(json.dumps(identities))
