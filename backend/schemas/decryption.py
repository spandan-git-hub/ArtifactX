"""
Pydantic schemas for the Cryptographic Decryption Subsystem.
Strictly adheres to master.md R5:
- Key fields use SecretStr and repr=False.
- Secrets are never echoed in serialization or string representations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class FormatDetectionResponse(BaseModel):
    """Result of format and entropy inspection."""
    model_config = ConfigDict(from_attributes=True)

    is_encrypted: bool
    format: Optional[str] = None
    confidence: float = 0.0
    entropy: float = 0.0
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)


class DecryptionRunRequest(BaseModel):
    """
    Investigator request to decrypt an encrypted evidence container.
    Key material is processed in ephemeral memory and never logged, echoed, or stored (master.md R5).
    """
    model_config = ConfigDict(extra="ignore")

    key_type: Optional[str] = Field(
        None,
        description="crypt14_keyfile | crypt15_hex | crypt15_keyfile",
    )
    key_data: Optional[SecretStr] = Field(
        None,
        repr=False,
        description="Key hex string or base64-encoded key file (redacted from repr/logs)",
    )
    key_material: Optional[SecretStr] = Field(
        None,
        repr=False,
        description="Legacy field for key hex or base64 key file (redacted from repr/logs)",
    )
    format_override: Optional[str] = Field(
        None,
        description="Explicit format override (e.g. crypt14, crypt15)",
    )
    candidate_file_id: Optional[int] = Field(
        None,
        description="EvidenceFile ID if targeting an extracted archive member",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Algorithm options (iterations, etc.)",
    )


class DecryptionOperationResponse(BaseModel):
    """Status and judicial provenance of a decryption operation."""
    model_config = ConfigDict(from_attributes=True)

    operation_id: int
    case_id: int
    evidence_id: int
    file_id: Optional[int] = None
    format: str
    status: str  # QUEUED, RUNNING, SUCCEEDED, FAILED, DECRYPTOR_NOT_AVAILABLE
    input_sha256: str
    output_sha256: Optional[str] = None
    derived_artifact_id: Optional[int] = None
    validation: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DerivedArtifactResponse(BaseModel):
    """Forensic catalog entry for a verified derived exhibit stored in PostgreSQL."""
    model_config = ConfigDict(from_attributes=True)

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
