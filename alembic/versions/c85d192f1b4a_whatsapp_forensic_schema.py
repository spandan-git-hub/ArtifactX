"""whatsapp_forensic_schema

Revision ID: c85d192f1b4a
Revises: f37bcf5c3ce1
Create Date: 2026-10-15 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c85d192f1b4a'
down_revision: Union[str, Sequence[str], None] = 'f37bcf5c3ce1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: WhatsApp forensic columns and auxiliary tables (spec B7.5)."""
    # 1. Add forensic columns to wa_messages
    with op.batch_alter_table('wa_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('key_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('chat_row_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('message_type_code', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('message_type_name', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('ts_raw', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('ts_unit', sa.String(length=20), nullable=True, server_default='ms'))
        batch_op.add_column(sa.Column('ts_utc_ms', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('received_ts_raw', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('source_table', sa.String(length=100), nullable=True, server_default='message'))
        batch_op.add_column(sa.Column('source_row_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('derived_artifact_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('evidence_sha256', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('quoted_row_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('location_lat', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('location_lon', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('is_edited', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('flags', sa.JSON(), nullable=True, server_default='[]'))

        batch_op.create_index('ix_wa_messages_key_id', ['key_id'], unique=False)
        batch_op.create_index('ix_wa_messages_chat_row_id', ['chat_row_id'], unique=False)
        batch_op.create_index('ix_wa_messages_ts_utc_ms', ['ts_utc_ms'], unique=False)

    # 2. Create wa_revocations table (B7.4, B7.5)
    op.create_table(
        'wa_revocations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id'), nullable=False),
        sa.Column('derived_artifact_id', sa.String(length=255), nullable=True),
        sa.Column('message_row_id', sa.Integer(), nullable=True),
        sa.Column('revoked_key_id', sa.String(length=255), nullable=False),
        sa.Column('revoke_ts', sa.BigInteger(), nullable=True),
        sa.Column('admin_jid', sa.String(length=255), nullable=True),
        sa.Column('original_sender', sa.String(length=255), nullable=True),
        sa.Column('original_ts', sa.BigInteger(), nullable=True),
        sa.Column('finding_id', sa.String(length=64), nullable=True),
        sa.Column('confidence_score', sa.Float(), server_default='1.0'),
        sa.Column('strength', sa.String(length=50), server_default='deterministic'),
        sa.Column('limitations', sa.JSON(), server_default='[]'),
        sa.Column('provenance', sa.JSON(), server_default='{}'),
    )
    op.create_index('ix_wa_revocations_revoked_key_id', 'wa_revocations', ['revoked_key_id'], unique=False)
    op.create_index('ix_wa_revocations_finding_id', 'wa_revocations', ['finding_id'], unique=False)

    # 3. Create wa_edits table (B7.4, B7.5)
    op.create_table(
        'wa_edits',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id'), nullable=False),
        sa.Column('derived_artifact_id', sa.String(length=255), nullable=True),
        sa.Column('message_row_id', sa.Integer(), nullable=True),
        sa.Column('original_key_id', sa.String(length=255), nullable=False),
        sa.Column('edited_ts', sa.BigInteger(), nullable=True),
        sa.Column('sender_ts', sa.BigInteger(), nullable=True),
        sa.Column('prior_text_not_present', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('edited_text', sa.Text(), nullable=True),
        sa.Column('finding_id', sa.String(length=64), nullable=True),
        sa.Column('confidence_score', sa.Float(), server_default='1.0'),
        sa.Column('strength', sa.String(length=50), server_default='deterministic'),
        sa.Column('limitations', sa.JSON(), server_default='[]'),
        sa.Column('provenance', sa.JSON(), server_default='{}'),
    )
    op.create_index('ix_wa_edits_original_key_id', 'wa_edits', ['original_key_id'], unique=False)
    op.create_index('ix_wa_edits_finding_id', 'wa_edits', ['finding_id'], unique=False)

    # 4. Create wa_chats table (B7.2, B7.5)
    op.create_table(
        'wa_chats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id'), nullable=False),
        sa.Column('chat_row_id', sa.Integer(), nullable=True),
        sa.Column('jid', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=512), nullable=True),
        sa.Column('is_group', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('hidden', sa.Integer(), server_default='0'),
        sa.Column('archived', sa.Integer(), server_default='0'),
        sa.Column('last_message_row_id', sa.Integer(), nullable=True),
        sa.Column('participant_jids', sa.JSON(), server_default='[]'),
        sa.Column('provenance', sa.JSON(), server_default='{}'),
    )
    op.create_index('ix_wa_chats_jid', 'wa_chats', ['jid'], unique=False)
    op.create_index('ix_wa_chats_chat_row_id', 'wa_chats', ['chat_row_id'], unique=False)

    # 5. Create wa_jids table (B7.2, B7.5)
    op.create_table(
        'wa_jids',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id'), nullable=False),
        sa.Column('jid_row_id', sa.Integer(), nullable=True),
        sa.Column('raw_string', sa.String(length=255), nullable=False),
        sa.Column('user', sa.String(length=255), nullable=True),
        sa.Column('server', sa.String(length=255), nullable=True),
        sa.Column('jid_type', sa.Integer(), server_default='0'),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('is_group', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('provenance', sa.JSON(), server_default='{}'),
    )
    op.create_index('ix_wa_jids_raw_string', 'wa_jids', ['raw_string'], unique=False)
    op.create_index('ix_wa_jids_jid_row_id', 'wa_jids', ['jid_row_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema: remove WhatsApp tables and forensic columns."""
    op.drop_table('wa_jids')
    op.drop_table('wa_chats')
    op.drop_table('wa_edits')
    op.drop_table('wa_revocations')

    with op.batch_alter_table('wa_messages', schema=None) as batch_op:
        batch_op.drop_index('ix_wa_messages_ts_utc_ms')
        batch_op.drop_index('ix_wa_messages_chat_row_id')
        batch_op.drop_index('ix_wa_messages_key_id')
        batch_op.drop_column('flags')
        batch_op.drop_column('is_edited')
        batch_op.drop_column('is_revoked')
        batch_op.drop_column('location_lon')
        batch_op.drop_column('location_lat')
        batch_op.drop_column('quoted_row_id')
        batch_op.drop_column('evidence_sha256')
        batch_op.drop_column('derived_artifact_id')
        batch_op.drop_column('source_row_id')
        batch_op.drop_column('source_table')
        batch_op.drop_column('received_ts_raw')
        batch_op.drop_column('ts_utc_ms')
        batch_op.drop_column('ts_unit')
        batch_op.drop_column('ts_raw')
        batch_op.drop_column('message_type_name')
        batch_op.drop_column('message_type_code')
        batch_op.drop_column('chat_row_id')
        batch_op.drop_column('key_id')
