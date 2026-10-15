"""recovery_findings_schema

Revision ID: e10a28f4c71b
Revises: d94e183a6b2c
Create Date: 2026-10-15 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e10a28f4c71b'
down_revision: Union[str, Sequence[str], None] = 'd94e183a6b2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add B10 deleted-data recovery forensic columns to recovered_findings."""
    with op.batch_alter_table('recovered_findings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('finding_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('tier', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('kind', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('strength', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('confidence_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('table_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('frame_index', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('recovered_fields', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('view', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('evidence_sha256', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('candidate_original_text', sa.Text(), nullable=True))

        batch_op.create_index(batch_op.f('ix_recovered_findings_finding_id'), ['finding_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_recovered_findings_tier'), ['tier'], unique=False)
        batch_op.create_index(batch_op.f('ix_recovered_findings_kind'), ['kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_recovered_findings_strength'), ['strength'], unique=False)
        batch_op.create_index(batch_op.f('ix_recovered_findings_table_name'), ['table_name'], unique=False)
        batch_op.create_index(batch_op.f('ix_recovered_findings_evidence_sha256'), ['evidence_sha256'], unique=False)


def downgrade() -> None:
    """Remove B10 forensic columns from recovered_findings."""
    with op.batch_alter_table('recovered_findings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recovered_findings_evidence_sha256'))
        batch_op.drop_index(batch_op.f('ix_recovered_findings_table_name'))
        batch_op.drop_index(batch_op.f('ix_recovered_findings_strength'))
        batch_op.drop_index(batch_op.f('ix_recovered_findings_kind'))
        batch_op.drop_index(batch_op.f('ix_recovered_findings_tier'))
        batch_op.drop_index(batch_op.f('ix_recovered_findings_finding_id'))

        batch_op.drop_column('candidate_original_text')
        batch_op.drop_column('evidence_sha256')
        batch_op.drop_column('view')
        batch_op.drop_column('recovered_fields')
        batch_op.drop_column('frame_index')
        batch_op.drop_column('table_name')
        batch_op.drop_column('confidence_score')
        batch_op.drop_column('strength')
        batch_op.drop_column('kind')
        batch_op.drop_column('tier')
        batch_op.drop_column('finding_id')
