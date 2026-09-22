"""Fence concurrent billing reconciliation snapshots.

Revision: b872de3c4021
Revises: e094ab60ff70
"""

import sqlalchemy as sa
from alembic import op

revision = "b872de3c4021"
down_revision = "e094ab60ff70"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workspaces", sa.Column("billing_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("workspaces", "billing_version")
