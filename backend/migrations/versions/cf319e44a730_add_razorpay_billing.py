"""Add Standard Checkout order references and term-limited billing."""

import sqlalchemy as sa
from alembic import op

revision = "cf319e44a730"
down_revision = "b23fd18c4e20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workspaces", sa.Column("razorpay_order_id", sa.String(), nullable=True))
    op.add_column("workspaces", sa.Column("razorpay_order_amount_paise", sa.Integer(), nullable=True))
    op.add_column("workspaces", sa.Column("razorpay_order_plan", sa.String(), nullable=False, server_default=""))
    op.add_column("workspaces", sa.Column("razorpay_order_period", sa.String(), nullable=False, server_default=""))
    op.add_column("workspaces", sa.Column("razorpay_payment_id", sa.String(), nullable=True))
    op.add_column("workspaces", sa.Column("billing_provider", sa.String(), nullable=False, server_default=""))
    op.add_column("workspaces", sa.Column("billing_expires_at", sa.Float(), nullable=True))
    op.create_index("uq_workspaces_razorpay_order_id", "workspaces", ["razorpay_order_id"], unique=True)
    op.create_index("uq_workspaces_razorpay_payment_id", "workspaces", ["razorpay_payment_id"], unique=True)
    op.execute(
        "UPDATE workspaces SET billing_provider = 'stripe' "
        "WHERE stripe_customer_id IS NOT NULL OR stripe_subscription_id IS NOT NULL"
    )


def downgrade():
    op.drop_index("uq_workspaces_razorpay_payment_id", table_name="workspaces")
    op.drop_index("uq_workspaces_razorpay_order_id", table_name="workspaces")
    op.drop_column("workspaces", "billing_expires_at")
    op.drop_column("workspaces", "billing_provider")
    op.drop_column("workspaces", "razorpay_payment_id")
    op.drop_column("workspaces", "razorpay_order_period")
    op.drop_column("workspaces", "razorpay_order_plan")
    op.drop_column("workspaces", "razorpay_order_amount_paise")
    op.drop_column("workspaces", "razorpay_order_id")
