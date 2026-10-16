"""
Pydantic schemas for forensic pipeline orchestration API (spec B13.2).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class KeyMaterialInput(BaseModel):
    """Input key material for encrypted exhibit decryption (R5)."""

    model_config = ConfigDict(extra="ignore")

    key_type: str = Field(default="crypt14", description="crypt14 | crypt15 | raw")
    key_hex: Optional[str] = Field(default=None, description="Hex-encoded 32-byte AES key")
    key_file_b64: Optional[str] = Field(default=None, description="Base64-encoded key file bytes")


class PipelineRunRequest(BaseModel):
    """Request payload to initiate an end-to-end pipeline execution run."""

    model_config = ConfigDict(extra="ignore")

    evidence_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of evidence exhibit IDs to include. Defaults to all exhibits in the case.",
    )
    keys: Optional[List[KeyMaterialInput]] = Field(
        default=None,
        description="Optional cryptographic keys for encrypted containers (Crypt14/Crypt15). Excluded from middleware capture per R5.",
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional threshold and execution overrides.",
    )


class PipelineStageRunResponse(BaseModel):
    """Detailed response representation of an individual pipeline stage."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    stage: str
    evidence_id: Optional[str] = None
    status: str
    error_code: Optional[str] = None
    skip_reason: Optional[str] = None
    counts_json: Optional[Dict[str, Any]] = None
    output_hash: Optional[str] = None
    duration_ms: Optional[float] = None
    errors_json: Optional[List[str]] = None


class PipelineRunSummaryResponse(BaseModel):
    """Compact summary of a pipeline run for case-level listings (R19)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: int
    status: str
    content_hash: Optional[str] = None
    summary_json: Optional[Dict[str, Any]] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class PipelineRunDetailResponse(BaseModel):
    """Full detail view of a pipeline run including all stage records."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: int
    status: str
    content_hash: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    summary_json: Optional[Dict[str, Any]] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    stage_runs: List[PipelineStageRunResponse] = Field(default_factory=list)
