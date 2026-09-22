"""Opt-in candidate discovery and revocable resume access, without exposing interviews."""

import sqlalchemy as sa
from alembic import op

revision = "f781c42d930a"
down_revision = "e54c91d703a2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("resumes", sa.Column("extracted_text", sa.String(), nullable=True))
    op.create_table(
        "recruiter_profiles",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("job_title", sa.String(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("headline", sa.String(), nullable=False),
        sa.Column("target_role", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("discoverable", sa.Boolean(), nullable=False),
        sa.Column("resume_id", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
    )
    for name in ("workspace_id", "discoverable"):
        op.create_index(f"ix_candidate_profiles_{name}", "candidate_profiles", [name])
    op.create_table(
        "resume_access_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("candidate_profile_id", sa.String(), sa.ForeignKey("candidate_profiles.id"), nullable=False),
        sa.Column("recruiter_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resume_id", sa.String(), nullable=False),
        sa.Column("recruiter_name", sa.String(), nullable=False),
        sa.Column("recruiter_email", sa.String(), nullable=False),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("job_title", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("decided_at", sa.Float(), nullable=True),
        sa.UniqueConstraint("candidate_profile_id", "recruiter_user_id"),
    )
    for name in ("candidate_profile_id", "recruiter_user_id"):
        op.create_index(f"ix_resume_access_requests_{name}", "resume_access_requests", [name])


def downgrade():
    op.drop_table("resume_access_requests")
    op.drop_table("candidate_profiles")
    op.drop_table("recruiter_profiles")
    op.drop_column("resumes", "extracted_text")
