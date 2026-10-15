"""timeline_forensic_schema

Revision ID: b11a78e910cd
Revises: e10a28f4c71b
Create Date: 2026-10-15 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b11a78e910cd'
down_revision: Union[str, Sequence[str], None] = 'e10a28f4c71b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add B11 timeline & time handling forensic columns to timeline_events."""
    with op.batch_alter_table('timeline_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('event_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('utc_ms', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('time_unit', sa.String(length=32), nullable=True, server_default='unknown'))
        batch_op.add_column(sa.Column('tz_basis', sa.String(length=32), nullable=True, server_default='utc_source'))
        batch_op.add_column(sa.Column('time_flags', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('raw_timestamp', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('actor_ref', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('chat_ref', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source_refs', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('confidence_score', sa.Float(), nullable=True, server_default='1.0'))
        batch_op.add_column(sa.Column('strength', sa.String(length=32), nullable=True, server_default='deterministic'))
        batch_op.add_column(sa.Column('limitations', sa.JSON(), nullable=True))

        batch_op.create_index(batch_op.f('ix_timeline_events_event_id'), ['event_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_timeline_events_utc_ms'), ['utc_ms'], unique=False)


def downgrade() -> None:
    """Remove B11 forensic columns from timeline_events."""
    with op.batch_alter_table('timeline_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_timeline_events_utc_ms'))
        batch_op.drop_index(batch_op.f('ix_timeline_events_event_id'))

        batch_op.drop_column('limitations')
        batch_op.drop_column('strength')
        batch_op.drop_column('confidence_score')
        batch_op.drop_column('source_refs')
        batch_op.drop_column('summary')
        batch_op.drop_column('chat_ref')
        batch_op.drop_column('actor_ref')
        batch_op.drop_column('raw_timestamp')
        batch_op.drop_column('time_flags')
        batch_op.drop_column('tz_basis')
        batch_op.drop_column('time_unit')
        batch_op.drop_column('utc_ms')
        batch_op.drop_column('event_id')
