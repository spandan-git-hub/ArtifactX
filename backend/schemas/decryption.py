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
    key_file_id: Optional[int] = Field(
        None,
        description="Optional EvidenceFile ID of detected key file",
    )
    evidence_id: Optional[int] = Field(
        None,
        description="Optional Evidence ID if targeting case-wide execution",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Algorithm options (iterations, etc.)",
    )


class CandidateKeyInfo(BaseModel):
    """Candidate key found in evidence relevant to an encrypted file."""
    model_config = ConfigDict(from_attributes=True)

    key_file_id: int
    filename: str
    relative_path: str
    key_type: str
    key_format: str
    size_bytes: int
    preview_hex: str
    autofill_value: str
    is_matched: bool = False


class DiscoveredKeyInfo(BaseModel):
    """Cryptographic key file identified across case evidence files."""
    model_config = ConfigDict(from_attributes=True)

    key_file_id: int
    filename: str
    relative_path: str
    key_type: str
    size_bytes: int
    source_container: str
    preview_hex: str
    autofill_value: str


class EncryptedFileInfo(BaseModel):
    """File identified from evidence that requires cryptographic decryption."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    evidence_id: int
    file_id: Optional[int] = None
    filename: str
    relative_path: str
    size_bytes: int
    sha256: str
    detected_format: str
    format_name: str
    source_container: str
    status: str
    derived_artifact_id: Optional[int] = None
    candidate_keys: List[CandidateKeyInfo] = Field(default_factory=list)
    autofill_key: Optional[CandidateKeyInfo] = None


class DirectlyUsableFileInfo(BaseModel):
    """File identified from evidence or derived exhibit that is directly accessible."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_derived: bool = False
    artifact_id: Optional[int] = None
    evidence_id: int
    file_id: Optional[int] = None
    filename: str
    relative_path: str
    size_bytes: int
    sha256: str
    category: str
    mime_type: Optional[str] = None
    source_container: str
    status: str
    table_count: Optional[int] = None
    tables: List[str] = Field(default_factory=list)


class DecryptionInventoryStats(BaseModel):
    """Counts for encrypted and directly usable file groups."""
    model_config = ConfigDict(from_attributes=True)

    total_identified_files: int
    encrypted_count: int
    directly_usable_count: int
    discovered_keys_count: int
    decrypted_count: int


class DecryptionInventoryResponse(BaseModel):
    """Comprehensive inventory of identified evidence files grouped into encrypted and usable sections."""
    model_config = ConfigDict(from_attributes=True)

    case_id: int
    encrypted_files: List[EncryptedFileInfo] = Field(default_factory=list)
    directly_usable_files: List[DirectlyUsableFileInfo] = Field(default_factory=list)
    discovered_keys: List[DiscoveredKeyInfo] = Field(default_factory=list)
    stats: DecryptionInventoryStats


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
