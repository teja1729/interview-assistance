"""Deduplicate immutable prompts and relate repeated practice goals to source interviews.

Revision: d20a77b9c431
Revises: c91f0326ad10
"""

import sqlalchemy as sa
from alembic import op

revision = "d20a77b9c431"
down_revision = "c91f0326ad10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "prompt_bundles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("prompts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
    )
    op.add_column("practice_tasks", sa.Column("skill_id", sa.String(), nullable=True))
    op.add_column("practice_tasks", sa.Column("exercise_type", sa.String(), nullable=True))
    op.add_column("practice_tasks", sa.Column("active_key", sa.String(), nullable=True))
    op.create_index("ix_practice_tasks_active_key", "practice_tasks", ["active_key"], unique=True)
    op.create_table(
        "practice_task_sources",
        sa.Column("task_id", sa.String(), sa.ForeignKey("practice_tasks.id"), primary_key=True),
        sa.Column("interview_id", sa.String(), sa.ForeignKey("interviews.id"), primary_key=True),
    )
    op.execute("INSERT INTO practice_task_sources (task_id, interview_id) SELECT id, interview_id FROM practice_tasks")


def downgrade():
    op.drop_table("practice_task_sources")
    op.drop_index("ix_practice_tasks_active_key", table_name="practice_tasks")
    for name in ("active_key", "exercise_type", "skill_id"):
        op.drop_column("practice_tasks", name)
    op.drop_table("prompt_bundles")
