"""correlation_findings_schema

Revision ID: b12c77f022ef
Revises: b11a78e910cd
Create Date: 2026-10-15 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b12c77f022ef'
down_revision: Union[str, Sequence[str], None] = 'b11a78e910cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add B12 correlation findings forensic columns to correlation_findings."""
    with op.batch_alter_table('correlation_findings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('finding_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('kind', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('strength', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('match_certainty', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('thresholds_version', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('normalized_value', sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column('left_ref', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('right_ref', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('ambiguity', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('below_threshold', sa.Boolean(), nullable=True, server_default=sa.text('false')))

        batch_op.create_index(batch_op.f('ix_correlation_findings_finding_id'), ['finding_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_correlation_findings_kind'), ['kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_correlation_findings_strength'), ['strength'], unique=False)
        batch_op.create_index(batch_op.f('ix_correlation_findings_normalized_value'), ['normalized_value'], unique=False)
        batch_op.create_index(batch_op.f('ix_correlation_findings_below_threshold'), ['below_threshold'], unique=False)


def downgrade() -> None:
    """Remove B12 correlation findings forensic columns from correlation_findings."""
    with op.batch_alter_table('correlation_findings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_correlation_findings_below_threshold'))
        batch_op.drop_index(batch_op.f('ix_correlation_findings_normalized_value'))
        batch_op.drop_index(batch_op.f('ix_correlation_findings_strength'))
        batch_op.drop_index(batch_op.f('ix_correlation_findings_kind'))
        batch_op.drop_index(batch_op.f('ix_correlation_findings_finding_id'))

        batch_op.drop_column('below_threshold')
        batch_op.drop_column('ambiguity')
        batch_op.drop_column('right_ref')
        batch_op.drop_column('left_ref')
        batch_op.drop_column('normalized_value')
        batch_op.drop_column('thresholds_version')
        batch_op.drop_column('match_certainty')
        batch_op.drop_column('strength')
        batch_op.drop_column('kind')
        batch_op.drop_column('finding_id')
