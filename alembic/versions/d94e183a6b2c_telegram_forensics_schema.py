"""telegram_forensics_schema

Revision ID: d94e183a6b2c
Revises: c85d192f1b4a
Create Date: 2026-10-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd94e183a6b2c'
down_revision: Union[str, Sequence[str], None] = 'c85d192f1b4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Telegram forensic columns and auxiliary tables (spec B9.6)."""
    # 1. Add evidence set columns to evidence table (B9.5)
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.add_column(sa.Column('evidence_set_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('evidence_role', sa.String(length=50), nullable=True))
        batch_op.create_index(batch_op.f('ix_evidence_evidence_set_id'), ['evidence_set_id'], unique=False)

    # 2. Add forensic columns to tg_messages (B9.6)
    with op.batch_alter_table('tg_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mid', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('from_id', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('out', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('text', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('date_raw', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('date_unit', sa.String(length=20), nullable=True, server_default='seconds'))
        batch_op.add_column(sa.Column('date_utc_ms', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('media_kind', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('media_ref', sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column('reply_to_mid', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('geo_lat', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('geo_lon', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('entities', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('flags', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('read_state', sa.Integer(), nullable=True, server_default='1'))
        batch_op.add_column(sa.Column('send_state', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('view', sa.String(length=50), nullable=True, server_default='main_view'))
        batch_op.add_column(sa.Column('source_table', sa.String(length=100), nullable=True, server_default='messages_v2'))
        batch_op.add_column(sa.Column('source_row_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('finding_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('confidence_score', sa.Float(), nullable=True, server_default='1.0'))
        batch_op.add_column(sa.Column('strength', sa.String(length=50), nullable=True, server_default='deterministic'))
        batch_op.add_column(sa.Column('provenance', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('limitations', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('trailing_bytes_info', sa.JSON(), nullable=True))
        batch_op.create_index(batch_op.f('ix_tg_messages_mid'), ['mid'], unique=False)
        batch_op.create_index(batch_op.f('ix_tg_messages_date_utc_ms'), ['date_utc_ms'], unique=False)
        batch_op.create_index(batch_op.f('ix_tg_messages_finding_id'), ['finding_id'], unique=False)

    # 3. Create tg_dialogs
    op.create_table(
        'tg_dialogs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('dialog_id', sa.BigInteger(), nullable=False),
        sa.Column('peer_kind', sa.String(length=50), nullable=False),
        sa.Column('peer_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=True),
        sa.Column('last_mid', sa.Integer(), nullable=True),
        sa.Column('unread_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('pinned', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('finding_id', sa.String(length=64), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=True),
        sa.Column('limitations', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tg_dialogs_dialog_id'), 'tg_dialogs', ['dialog_id'], unique=False)
    op.create_index(op.f('ix_tg_dialogs_finding_id'), 'tg_dialogs', ['finding_id'], unique=False)

    # 4. Create tg_users
    op.create_table(
        'tg_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('uid', sa.BigInteger(), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('is_self', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('contact', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('deleted', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('bot', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('finding_id', sa.String(length=64), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tg_users_uid'), 'tg_users', ['uid'], unique=False)
    op.create_index(op.f('ix_tg_users_finding_id'), 'tg_users', ['finding_id'], unique=False)

    # 5. Create tg_chats
    op.create_table(
        'tg_chats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('did', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('is_channel', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('is_group', sa.Boolean(), nullable=True, server_default=sa.text('1')),
        sa.Column('participants_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('participant_uids', sa.JSON(), nullable=True),
        sa.Column('finding_id', sa.String(length=64), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tg_chats_did'), 'tg_chats', ['did'], unique=False)
    op.create_index(op.f('ix_tg_chats_chat_id'), 'tg_chats', ['chat_id'], unique=False)
    op.create_index(op.f('ix_tg_chats_finding_id'), 'tg_chats', ['finding_id'], unique=False)

    # 6. Create tg_unparsed_blobs
    op.create_table(
        'tg_unparsed_blobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('table', sa.String(length=100), nullable=False),
        sa.Column('row_id', sa.Integer(), nullable=False),
        sa.Column('mid', sa.Integer(), nullable=True),
        sa.Column('uid', sa.BigInteger(), nullable=True),
        sa.Column('constructor_id_hex', sa.String(length=20), nullable=True),
        sa.Column('length', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('container_metadata', sa.JSON(), nullable=True),
        sa.Column('finding_id', sa.String(length=64), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tg_unparsed_blobs_mid'), 'tg_unparsed_blobs', ['mid'], unique=False)
    op.create_index(op.f('ix_tg_unparsed_blobs_uid'), 'tg_unparsed_blobs', ['uid'], unique=False)
    op.create_index(op.f('ix_tg_unparsed_blobs_finding_id'), 'tg_unparsed_blobs', ['finding_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema: remove Telegram forensic tables and columns."""
    op.drop_table('tg_unparsed_blobs')
    op.drop_table('tg_chats')
    op.drop_table('tg_users')
    op.drop_table('tg_dialogs')

    with op.batch_alter_table('tg_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tg_messages_finding_id'))
        batch_op.drop_index(batch_op.f('ix_tg_messages_date_utc_ms'))
        batch_op.drop_index(batch_op.f('ix_tg_messages_mid'))
        batch_op.drop_column('trailing_bytes_info')
        batch_op.drop_column('limitations')
        batch_op.drop_column('provenance')
        batch_op.drop_column('strength')
        batch_op.drop_column('confidence_score')
        batch_op.drop_column('finding_id')
        batch_op.drop_column('source_row_id')
        batch_op.drop_column('source_table')
        batch_op.drop_column('view')
        batch_op.drop_column('send_state')
        batch_op.drop_column('read_state')
        batch_op.drop_column('flags')
        batch_op.drop_column('entities')
        batch_op.drop_column('geo_lon')
        batch_op.drop_column('geo_lat')
        batch_op.drop_column('reply_to_mid')
        batch_op.drop_column('media_path')
        batch_op.drop_column('media_ref')
        batch_op.drop_column('media_kind')
        batch_op.drop_column('date_utc_ms')
        batch_op.drop_column('date_unit')
        batch_op.drop_column('date_raw')
        batch_op.drop_column('text')
        batch_op.drop_column('out')
        batch_op.drop_column('from_id')
        batch_op.drop_column('mid')

    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_evidence_evidence_set_id'))
        batch_op.drop_column('evidence_role')
        batch_op.drop_column('evidence_set_id')
