"""add demo sandbox flags (ADR 0021)

Revision ID: 7c1d2e3f4a5b
Revises: 5ad6dc481293
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "7c1d2e3f4a5b"
down_revision = "5ad6dc481293"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.add_column(
            sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False)
        )
        batch_op.add_column(sa.Column("demo_expires_at", sa.DateTime(timezone=True), nullable=True))
    # The hourly purge looks for expired demos only: index exactly those rows.
    op.create_index(
        "ix_organizations_demo_expiry",
        "organizations",
        ["demo_expires_at"],
        postgresql_where=sa.text("is_demo"),
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_demo")
    op.drop_index("ix_organizations_demo_expiry", table_name="organizations")
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_column("demo_expires_at")
        batch_op.drop_column("is_demo")
