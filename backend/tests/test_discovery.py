"""Consent is enforced at every boundary, independently of the recruiter UI."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlmodel import Session

from app.models import Resume


def publish(client, engine, **changes):
    with Session(engine) as session:
        resume = Resume(
            workspace_id=client.workspace_id,
            user_id=client.user_id,
            name="Engineering resume",
            filename="resume.txt",
            mime="text/plain",
            digest="Private AI analysis",
            extracted_text="Original candidate resume text.",
        )
        session.add(resume)
        session.commit()
        resume_id = resume.id
    body = {
        "display_name": "Alex Candidate",
        "target_role": "Software Engineer",
        "experience_years": 4,
        "skills": ["Python"],
        "resume_id": resume_id,
        "discoverable": True,
        **changes,
    }
    result = client.put("/api/candidate-profile", json=body)
    assert result.status_code == 200, result.text
    return result.json(), body


def recruit(clients):
    client = clients("recruiter@example.test")
    assert (
        client.put("/api/recruiter/profile", json={"company_name": "Example Ltd", "job_title": "Recruiter"}).status_code
        == 200
    )
    return client


def ask(recruiter, profile):
    result = recruiter.post(
        f"/api/recruiter/candidates/{profile['id']}/request", json={"message": "Hiring for a Python engineering role."}
    )
    assert result.status_code == 200, result.text
    return result.json()


def test_real_consent_flow_and_isolation(clients, engine):
    owner, stranger = clients(), clients("other@example.test")
    recruiter = recruit(clients)
    assert owner.get("/api/recruiter/candidates").status_code == 403
    assert owner.get("/api/candidate-profile").json() is None
    profile, body = publish(owner, engine, discoverable=False)
    assert recruiter.get("/api/recruiter/candidates").json()["total"] == 0
    assert (
        recruiter.post(
            f"/api/recruiter/candidates/{profile['id']}/request", json={"message": "Please share your resume."}
        ).status_code
        == 404
    )
    owner.put("/api/candidate-profile", json={**body, "discoverable": True})
    listing = recruiter.get("/api/recruiter/candidates?q=engineer&min_experience=3").json()
    assert listing["total"] == 1
    assert set(listing["items"][0]) == {
        "id",
        "display_name",
        "headline",
        "target_role",
        "location",
        "experience_years",
        "skills",
        "updated_at",
    }
    assert recruiter.get("/api/recruiter/candidates?min_experience=5").json()["total"] == 0
    assert recruiter.get("/api/recruiter/candidates?q=%25").json()["total"] == 0
    request = ask(recruiter, profile)
    assert ask(recruiter, profile)["id"] == request["id"]
    url = f"/api/recruiter/requests/{request['id']}/resume"
    assert recruiter.get(url).status_code == 403
    decision = f"/api/candidate-requests/{request['id']}"
    assert stranger.patch(decision, json={"status": "approved"}).status_code == 404
    assert recruiter.patch(decision, json={"status": "approved"}).status_code == 404
    assert owner.patch(decision, json={"status": "approved"}).status_code == 200
    shared = recruiter.get(url)
    assert shared.status_code == 200
    assert shared.json()["text"] == "Original candidate resume text."
    assert shared.json()["email"] == "alex@example.test"
    assert "Private AI analysis" not in shared.text
    another = recruit(clients)
    assert another.get(url).status_code == 404
    assert recruiter.get(f"/api/resumes/{body['resume_id']}").status_code == 404
    assert owner.patch(decision, json={"status": "revoked"}).status_code == 200
    assert recruiter.get(url).status_code == 403


def test_withdraw_replace_delete_revoke_and_require_new_consent(clients, engine):
    owner, recruiter = clients(), recruit(clients)
    profile, body = publish(owner, engine)
    request = ask(recruiter, profile)
    decision = f"/api/candidate-requests/{request['id']}"
    url = f"/api/recruiter/requests/{request['id']}/resume"
    owner.patch(decision, json={"status": "approved"})
    owner.put("/api/candidate-profile", json={**body, "discoverable": False})
    assert recruiter.get(url).status_code == 403
    owner.put("/api/candidate-profile", json=body)
    assert recruiter.get(url).status_code == 403  # Republishing cannot resurrect approval.
    assert ask(recruiter, profile)["status"] == "pending"
    owner.patch(decision, json={"status": "approved"})
    profile, new_body = publish(owner, engine)
    assert recruiter.get(url).status_code == 403
    ask(recruiter, profile)
    owner.patch(decision, json={"status": "approved"})
    assert owner.delete(f"/api/resumes/{new_body['resume_id']}").status_code == 200
    assert recruiter.get(url).status_code == 403
    assert recruiter.get("/api/recruiter/candidates").json()["total"] == 0
    assert owner.get("/api/candidate-profile").json()["discoverable"] is False


def test_deny_persists_and_private_upload_cannot_be_selected(clients, engine):
    owner, other, recruiter = clients(), clients("other@example.test"), recruit(clients)
    profile, body = publish(owner, engine)
    assert other.put("/api/candidate-profile", json=body).status_code == 404
    request = ask(recruiter, profile)
    decision = f"/api/candidate-requests/{request['id']}"
    assert owner.patch(decision, json={"status": "denied"}).status_code == 200
    assert ask(recruiter, profile)["status"] == "denied"
    assert owner.patch(decision, json={"status": "approved"}).status_code == 409
    assert other.get("/api/candidate-requests").json() == []
    with Session(engine) as session:
        resume = session.get(Resume, body["resume_id"])
        resume.extracted_text = None
        session.add(resume)
        session.commit()
    assert owner.put("/api/candidate-profile", json=body).status_code == 422


def test_concurrent_duplicate_requests_have_one_record(clients, engine):
    owner, recruiter = clients(), recruit(clients)
    profile, _ = publish(owner, engine)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: ask(recruiter, profile), range(2)))
    assert results[0]["id"] == results[1]["id"]
    assert len(owner.get("/api/candidate-requests").json()) == 1


def test_recruiting_auth_csrf_and_input_contracts(clients):
    client = clients()
    assert client.put("/api/recruiter/profile", json={"company_name": "   "}).status_code == 422
    assert client.put("/api/recruiter/profile", json={"company_name": "Valid", "verified": True}).status_code == 422
    assert (
        client.put(
            "/api/recruiter/profile", json={"company_name": "Valid"}, headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    client.cookies.clear()
    for path in (
        "recruiter/profile",
        "recruiter/candidates",
        "recruiter/requests",
        "candidate-profile",
        "candidate-requests",
    ):
        assert client.get(f"/api/{path}").status_code == 401


@pytest.mark.parametrize("delete_upload", [False, True])
def test_concurrent_approval_cannot_restore_withdrawn_access(clients, engine, delete_upload):
    owner, recruiter = clients(), recruit(clients)
    profile, body = publish(owner, engine)
    request = ask(recruiter, profile)
    barrier = Barrier(2)

    def approve():
        barrier.wait()
        return owner.patch(f"/api/candidate-requests/{request['id']}", json={"status": "approved"})

    def withdraw():
        barrier.wait()
        if delete_upload:
            return owner.delete(f"/api/resumes/{body['resume_id']}")
        return owner.put("/api/candidate-profile", json={**body, "discoverable": False})

    with ThreadPoolExecutor(max_workers=2) as executor:
        approval, withdrawal = executor.submit(approve), executor.submit(withdraw)
        assert approval.result().status_code in {200, 409}
        assert withdrawal.result().status_code == 200
    assert recruiter.get(f"/api/recruiter/requests/{request['id']}/resume").status_code == 403
    assert recruiter.get("/api/recruiter/candidates").json()["total"] == 0
