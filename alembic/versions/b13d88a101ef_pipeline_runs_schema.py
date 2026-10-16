"""pipeline_runs_schema (spec 11_PIPELINE_AND_E2E.md §B13.2)

Revision ID: b13d88a101ef
Revises: b12c77f022ef
Create Date: 2026-10-16 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b13d88a101ef'
down_revision: Union[str, Sequence[str], None] = 'b12c77f022ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pipeline_runs and pipeline_stage_runs tables."""
    op.create_table(
        'pipeline_runs',
        sa.Column('id', sa.String(length=64), primary_key=True, nullable=False),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('config_json', sa.JSON(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('summary_json', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_pipeline_runs_id'), 'pipeline_runs', ['id'], unique=False)
    op.create_index(op.f('ix_pipeline_runs_case_id'), 'pipeline_runs', ['case_id'], unique=False)
    op.create_index(op.f('ix_pipeline_runs_status'), 'pipeline_runs', ['status'], unique=False)
    op.create_index(op.f('ix_pipeline_runs_content_hash'), 'pipeline_runs', ['content_hash'], unique=False)

    op.create_table(
        'pipeline_stage_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), sa.ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('evidence_id', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('skip_reason', sa.String(length=255), nullable=True),
        sa.Column('counts_json', sa.JSON(), nullable=True),
        sa.Column('output_hash', sa.String(length=64), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('errors_json', sa.JSON(), nullable=True),
    )
    op.create_index(op.f('ix_pipeline_stage_runs_id'), 'pipeline_stage_runs', ['id'], unique=False)
    op.create_index(op.f('ix_pipeline_stage_runs_run_id'), 'pipeline_stage_runs', ['run_id'], unique=False)
    op.create_index(op.f('ix_pipeline_stage_runs_stage'), 'pipeline_stage_runs', ['stage'], unique=False)
    op.create_index(op.f('ix_pipeline_stage_runs_evidence_id'), 'pipeline_stage_runs', ['evidence_id'], unique=False)
    op.create_index(op.f('ix_pipeline_stage_runs_status'), 'pipeline_stage_runs', ['status'], unique=False)


def downgrade() -> None:
    """Drop pipeline_stage_runs and pipeline_runs tables."""
    op.drop_table('pipeline_stage_runs')
    op.drop_table('pipeline_runs')
