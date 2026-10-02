"""make audit logs append only

Revision ID: 5504754508ee
Revises: 567982aede09
Create Date: 2026-10-02 06:58:05.512240

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5504754508ee'
down_revision = '567982aede09'
branch_labels = None
depends_on = None


def upgrade():
    # Blocks UPDATE always and DELETE unless the explicit maintenance flag is set for the
    # current transaction (used by test teardown and future retention jobs only).
    op.execute(
        """
        CREATE FUNCTION audit_logs_block_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE'
               AND current_setting('propflow.audit_maintenance', true) = 'on' THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'audit_logs is append-only (% blocked)', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_block_mutation();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_block_mutation()")
