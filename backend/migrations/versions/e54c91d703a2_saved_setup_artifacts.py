"""Persist candidate-owned role briefs and title suggestions for explicit refresh/reuse.

Revision: e54c91d703a2
Revises: d20a77b9c431
"""

import sqlalchemy as sa
from alembic import op

revision = "e54c91d703a2"
down_revision = "d20a77b9c431"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "setup_artifacts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("cache_key", sa.String(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    for column in ("workspace_id", "user_id", "cache_key"):
        op.create_index(f"ix_setup_artifacts_{column}", "setup_artifacts", [column])


def downgrade():
    op.drop_table("setup_artifacts")
