from sqlmodel import Session

from app.models import Interview


def test_progress_counts_only_owned_completed_sessions_including_unscored(clients, engine):
    owner, other = clients(), clients("other@example.test")
    assert owner.get("/api/progress").json()["average_score"] is None
    with Session(engine) as session:
        for client, status, score in (
            (owner, "finished", 80),
            (owner, "finished", None),
            (owner, "active", 20),
            (other, "finished", 10),
        ):
            session.add(
                Interview(
                    workspace_id=client.workspace_id,
                    user_id=client.user_id,
                    job_title="Engineer",
                    status=status,
                    score=score,
                    ended_at=100,
                )
            )
        session.commit()
    result = owner.get("/api/progress")
    assert result.status_code == 200
    data = result.json()
    assert data["completed_interviews"] == 2
    assert data["scored_interviews"] == 1
    assert data["average_score"] == 80
    assert data["rounds"][0]["count"] == 2
    assert len(data["recent"]) == 2
    owner.cookies.clear()
    assert owner.get("/api/progress").status_code == 401
