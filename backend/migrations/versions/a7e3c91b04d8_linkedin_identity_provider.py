"""Allow Google and LinkedIn subjects to identify separate accounts.

Revision: a7e3c91b04d8
Revises: f781c42d930a
"""

import sqlalchemy as sa
from alembic import op

revision = "a7e3c91b04d8"
down_revision = "f781c42d930a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(), nullable=False, server_default="google"),
    )
    op.drop_index("ix_users_google_sub", table_name="users")
    op.create_index("ix_users_google_sub", "users", ["google_sub"])
    op.create_index("ix_users_auth_provider", "users", ["auth_provider"])
    op.create_index("uq_users_provider_subject", "users", ["auth_provider", "google_sub"], unique=True)


def downgrade():
    op.drop_index("uq_users_provider_subject", table_name="users")
    op.drop_index("ix_users_auth_provider", table_name="users")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.drop_column("users", "auth_provider")
