"""
Pydantic schemas for the Cryptographic Decryption Subsystem.
Strictly adheres to 09_API_DATA_CONTRACTS.md.
Never exposes raw cryptographic keys or passcodes in responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FormatDetectionResponse(BaseModel):
    """Result of format and entropy inspection."""
    is_encrypted: bool
    format: Optional[str] = None
    confidence: float = 0.0
    entropy: float = 0.0
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)


class DecryptionRunRequest(BaseModel):
    """
    Investigator request to decrypt an encrypted evidence container.
    Key material / passcodes are processed in ephemeral memory and never logged or stored.
    """
    key_material: Optional[str] = Field(None, description="WhatsApp key file (base64 or hex) or raw 32-byte key")
    passcode: Optional[str] = Field(None, description="Telegram in-app passcode / numeric PIN")
    format_override: Optional[str] = Field(None, description="Explicit format override (e.g. crypt12, crypt14, crypt15, sqlcipher, enc, mtproto)")
    candidate_file_id: Optional[int] = Field(None, description="EvidenceFile ID if targeting an extracted archive member")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Algorithm profile options (e.g. SQLCipher profile, iterations)")


class DecryptionOperationResponse(BaseModel):
    """Status and judicial provenance of a decryption operation."""
    operation_id: int
    case_id: int
    evidence_id: int
    file_id: Optional[int] = None
    format: str
    status: str  # QUEUED, RUNNING, SUCCEEDED, FAILED
    input_sha256: str
    output_sha256: Optional[str] = None
    derived_artifact_id: Optional[int] = None
    validation: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DerivedArtifactResponse(BaseModel):
    """Forensic catalog entry for a verified derived exhibit stored in PostgreSQL."""
    id: int
    case_id: int
    parent_evidence_id: int
    parent_file_id: Optional[int] = None
    original_filename: str
    artifact_type: str
    sha256: str
    size_bytes: int
    mime_type: Optional[str] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
