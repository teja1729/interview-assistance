"""Record terminal report job time for aggregate product metrics."""

import sqlalchemy as sa
from alembic import op

revision = "9a17d4c2f610"
down_revision = "a7e3c91b04d8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agent_jobs", sa.Column("completed_at", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("agent_jobs", "completed_at")
