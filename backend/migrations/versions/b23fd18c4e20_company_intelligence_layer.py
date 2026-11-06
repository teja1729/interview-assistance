"""Add versioned global company intelligence imports and immutable source rows."""

import sqlalchemy as sa
from alembic import op

revision = "b23fd18c4e20"
down_revision = "9a17d4c2f610"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "company_intelligence_imports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workbook_name", sa.String(), nullable=False),
        sa.Column("workbook_version", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="staged"),
        sa.Column("report", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("activated_at", sa.Float(), nullable=True),
    )
    op.create_index("ix_company_intelligence_imports_status", "company_intelligence_imports", ["status"])

    op.create_table(
        "company_intelligence_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("import_id", sa.String(), sa.ForeignKey("company_intelligence_imports.id"), nullable=False),
        sa.Column("sheet_name", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("company_key", sa.String(), nullable=False, server_default=""),
        sa.Column("role_family", sa.String(), nullable=False, server_default=""),
        sa.Column("publication_state", sa.String(), nullable=False, server_default="provisional"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("import_id", "sheet_name", "external_id"),
    )
    for column in ("import_id", "sheet_name", "external_id", "company_key", "role_family", "publication_state"):
        op.create_index(f"ix_company_intelligence_records_{column}", "company_intelligence_records", [column])
    op.create_index(
        "ix_company_intel_lookup",
        "company_intelligence_records",
        ["import_id", "company_key", "role_family", "publication_state"],
    )


def downgrade():
    op.drop_table("company_intelligence_records")
    op.drop_table("company_intelligence_imports")
