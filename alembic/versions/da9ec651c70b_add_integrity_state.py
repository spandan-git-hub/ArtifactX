"""add_integrity_state

Revision ID: da9ec651c70b
Revises: a77eef711395
Create Date: 2026-10-13 22:26:12.365244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da9ec651c70b'
down_revision: Union[str, Sequence[str], None] = 'a77eef711395'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema and migrate legacy evidence rows."""
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('integrity_state', sa.String(length=50), nullable=False, server_default='OK')
        )

    # Data migration: detect legacy rows with NULL content_bytes and flag as LEGACY_UNVERIFIABLE
    evidence_table = sa.table(
        'evidence',
        sa.column('integrity_state', sa.String),
        sa.column('content_bytes', sa.LargeBinary),
    )
    op.execute(
        evidence_table.update()
        .where(evidence_table.c.content_bytes.is_(None))
        .values(integrity_state='LEGACY_UNVERIFIABLE')
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.drop_column('integrity_state')
