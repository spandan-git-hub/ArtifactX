"""b5_ingest_integrity_audit

Revision ID: f37bcf5c3ce1
Revises: da9ec651c70b
Create Date: 2026-10-14 21:09:25.059011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f37bcf5c3ce1'
down_revision: Union[str, Sequence[str], None] = 'da9ec651c70b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: metadata, audit_log table, and immutability triggers."""
    # 1. Add Case metadata columns (B5.2)
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('case_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('examiner_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('examiner_designation', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('agency', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('legal_authority', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('jurisdiction', sa.String(length=255), nullable=True))
        batch_op.create_index('ix_cases_case_number', ['case_number'], unique=False)

    # 2. Add Evidence acquisition & multi-hash columns (B5.1, B5.2)
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acquisition_method', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('device_make_model', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('device_os_version', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('app_version', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('acquisition_time_utc', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('acquired_by', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('acquisition_hash_claimed', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('acquisition_hash_algorithm', sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column('claimed_vs_computed', sa.String(length=50), nullable=False, server_default='NOT_PROVIDED')
        )
        batch_op.add_column(sa.Column('sha512', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('md5', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('sha1', sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column('declared_mime', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('detected_format', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('uploader', sa.String(length=255), nullable=True))

    # 3. Add EvidenceFile multi-hash columns (B5.1)
    with op.batch_alter_table('evidence_files', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sha512', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('md5', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('sha1', sa.String(length=40), nullable=True))

    # 4. Create audit_log table (B5.5, DEC-010)
    op.create_table(
        'audit_log',
        sa.Column('seq', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ts_utc', sa.DateTime(), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=False, server_default='system'),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('evidence_id', sa.Integer(), nullable=True),
        sa.Column('details_json', sa.JSON(), nullable=False),
        sa.Column('prev_hash', sa.String(length=64), nullable=False),
        sa.Column('entry_hash', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('seq'),
    )
    op.create_index(op.f('ix_audit_log_seq'), 'audit_log', ['seq'], unique=False)
    op.create_index(op.f('ix_audit_log_ts_utc'), 'audit_log', ['ts_utc'], unique=False)
    op.create_index(op.f('ix_audit_log_action'), 'audit_log', ['action'], unique=False)
    op.create_index(op.f('ix_audit_log_case_id'), 'audit_log', ['case_id'], unique=False)
    op.create_index(op.f('ix_audit_log_evidence_id'), 'audit_log', ['evidence_id'], unique=False)
    op.create_index(op.f('ix_audit_log_entry_hash'), 'audit_log', ['entry_hash'], unique=False)

    # 5. Database-level triggers for immutability & append-only audit trail (B5.3, B5.5)
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_evidence_content_update
            BEFORE UPDATE OF content_bytes, sha256 ON evidence
            FOR EACH ROW
            WHEN OLD.content_bytes IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'Evidence content_bytes and sha256 are immutable');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_evidence_files_content_update
            BEFORE UPDATE OF content_bytes, sha256 ON evidence_files
            FOR EACH ROW
            WHEN OLD.content_bytes IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'EvidenceFile content_bytes and sha256 are immutable');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
            BEFORE UPDATE ON audit_log
            FOR EACH ROW
            BEGIN
                SELECT RAISE(ABORT, 'audit_log is append-only and immutable');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
            BEFORE DELETE ON audit_log
            FOR EACH ROW
            BEGIN
                SELECT RAISE(ABORT, 'audit_log entries cannot be deleted');
            END;
        """)
    elif dialect == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION prevent_evidence_update_fn()
            RETURNS trigger AS $$
            BEGIN
                IF OLD.content_bytes IS NOT NULL AND (NEW.content_bytes IS DISTINCT FROM OLD.content_bytes OR NEW.sha256 IS DISTINCT FROM OLD.sha256) THEN
                    RAISE EXCEPTION 'Evidence content_bytes and sha256 are immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            CREATE OR REPLACE TRIGGER trg_prevent_evidence_update
            BEFORE UPDATE ON evidence
            FOR EACH ROW EXECUTE FUNCTION prevent_evidence_update_fn();
        """)
        op.execute("""
            CREATE OR REPLACE TRIGGER trg_prevent_evidence_files_update
            BEFORE UPDATE ON evidence_files
            FOR EACH ROW EXECUTE FUNCTION prevent_evidence_update_fn();
        """)
        op.execute("""
            CREATE OR REPLACE FUNCTION prevent_audit_mutation_fn()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log is append-only and immutable';
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            CREATE OR REPLACE TRIGGER trg_prevent_audit_update
            BEFORE UPDATE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation_fn();
        """)
        op.execute("""
            CREATE OR REPLACE TRIGGER trg_prevent_audit_delete
            BEFORE DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation_fn();
        """)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS prevent_evidence_content_update;")
        op.execute("DROP TRIGGER IF EXISTS prevent_evidence_files_content_update;")
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update;")
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_log_delete;")
    elif dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_evidence_update ON evidence;")
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_evidence_files_update ON evidence_files;")
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_update ON audit_log;")
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_delete ON audit_log;")
        op.execute("DROP FUNCTION IF EXISTS prevent_evidence_update_fn;")
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_mutation_fn;")

    op.drop_table('audit_log')

    with op.batch_alter_table('evidence_files', schema=None) as batch_op:
        batch_op.drop_column('sha1')
        batch_op.drop_column('md5')
        batch_op.drop_column('sha512')

    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.drop_column('uploader')
        batch_op.drop_column('detected_format')
        batch_op.drop_column('declared_mime')
        batch_op.drop_column('sha1')
        batch_op.drop_column('md5')
        batch_op.drop_column('sha512')
        batch_op.drop_column('claimed_vs_computed')
        batch_op.drop_column('acquisition_hash_algorithm')
        batch_op.drop_column('acquisition_hash_claimed')
        batch_op.drop_column('acquired_by')
        batch_op.drop_column('acquisition_time_utc')
        batch_op.drop_column('app_version')
        batch_op.drop_column('device_os_version')
        batch_op.drop_column('device_make_model')
        batch_op.drop_column('acquisition_method')

    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.drop_index('ix_cases_case_number')
        batch_op.drop_column('jurisdiction')
        batch_op.drop_column('legal_authority')
        batch_op.drop_column('agency')
        batch_op.drop_column('examiner_designation')
        batch_op.drop_column('examiner_name')
        batch_op.drop_column('case_number')
