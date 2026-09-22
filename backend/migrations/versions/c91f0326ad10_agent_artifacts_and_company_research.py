"""Checkpoint agent stages, correlate attempts and cache private company research.

Revision: c91f0326ad10
Revises: b872de3c4021
"""

import sqlalchemy as sa
from alembic import op

revision = "c91f0326ad10"
down_revision = "b872de3c4021"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agent_jobs", sa.Column("artifacts", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("agent_runs", sa.Column("operation_id", sa.String(), nullable=True))
    op.add_column("agent_runs", sa.Column("stage", sa.String(), nullable=False, server_default="inference"))
    op.add_column("agent_runs", sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "company_research",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cache_key", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    for column in ("workspace_id", "user_id", "cache_key"):
        op.create_index(f"ix_company_research_{column}", "company_research", [column])


def downgrade():
    op.drop_table("company_research")
    for column in ("attempt", "stage", "operation_id"):
        op.drop_column("agent_runs", column)
    op.drop_column("agent_jobs", "artifacts")
