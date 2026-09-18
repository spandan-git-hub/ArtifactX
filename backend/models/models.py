"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.app.database import Base


class Case(Base):
    """Forensic case."""

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    investigator = Column(String(255))
    status = Column(String(50), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidence_items = relationship(
        "Evidence", back_populates="case", cascade="all, delete-orphan"
    )
    timeline_events = relationship("TimelineEvent", back_populates="case", cascade="all, delete-orphan")
    deleted_messages = relationship("DeletedMessage", back_populates="case", cascade="all, delete-orphan")
    media_items = relationship("MediaItem", back_populates="case", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="case", cascade="all, delete-orphan")
    correlation_edges = relationship("CorrelationEdge", cascade="all, delete-orphan")
    generated_reports = relationship("GeneratedReport", back_populates="case", cascade="all, delete-orphan")
    recovered_findings = relationship("RecoveredFinding", back_populates="case", cascade="all, delete-orphan")
    recovery_runs = relationship("RecoveryRun", back_populates="case", cascade="all, delete-orphan")
    derived_artifacts = relationship("DerivedArtifact", back_populates="case", cascade="all, delete-orphan")
    decryption_operations = relationship("DecryptionOperation", back_populates="case", cascade="all, delete-orphan")
    person_entities = relationship("PersonEntity", back_populates="case", cascade="all, delete-orphan")
    correlation_findings = relationship("CorrelationFinding", back_populates="case", cascade="all, delete-orphan")


class Evidence(Base):
    """An uploaded evidence file or ZIP package."""

    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    original_filename = Column(String(512), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    content_type = Column(String(255))
    evidence_type = Column(String(50))
    metadata_ = Column("metadata_", JSON, default=dict)
    extracted_path = Column(String(1024))
    content_bytes = Column(LargeBinary, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime)

    case = relationship("Case", back_populates="evidence_items")
    files = relationship("EvidenceFile", back_populates="evidence", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="evidence", cascade="all, delete-orphan")
    wa_messages = relationship("WhatsAppMessage", cascade="all, delete-orphan")
    wa_contacts = relationship("WhatsAppContact", cascade="all, delete-orphan")
    wa_groups = relationship("WhatsAppGroup", cascade="all, delete-orphan")
    tg_messages = relationship("TelegramMessage", cascade="all, delete-orphan")
    tg_contacts = relationship("TelegramContact", cascade="all, delete-orphan")
    tg_groups = relationship("TelegramGroup", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", cascade="all, delete-orphan")
    deleted_messages = relationship("DeletedMessage", cascade="all, delete-orphan")
    media_items = relationship("MediaItem", cascade="all, delete-orphan")
    analysis_logs = relationship("AnalysisLog", cascade="all, delete-orphan")
    derived_artifacts = relationship("DerivedArtifact", back_populates="evidence", cascade="all, delete-orphan")
    decryption_operations = relationship("DecryptionOperation", back_populates="evidence", cascade="all, delete-orphan")


class EvidenceFile(Base):
    """Individual files extracted from a ZIP package."""

    __tablename__ = "evidence_files"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    relative_path = Column(String(1024), nullable=False)
    sha256 = Column(String(64), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(255))
    metadata_ = Column("metadata_", JSON, default=dict)
    content_bytes = Column(LargeBinary, nullable=True)
    is_media = Column(Boolean, default=False)
    media_type = Column(String(50))

    evidence = relationship("Evidence", back_populates="files")


class AnalysisResult(Base):
    """Results of forensic analysis on evidence."""

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    analysis_type = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")
    results = Column(JSON, default=dict)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    evidence = relationship("Evidence", back_populates="analysis_results")


class WhatsAppMessage(Base):
    __tablename__ = "wa_messages"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    message_id = Column(String(255), index=True)
    key_remote_jid = Column(String(255), index=True)
    sender_jid = Column(String(255))
    participant_jid = Column(String(255))
    body = Column(Text)
    timestamp = Column(BigInteger, index=True)
    media_type = Column(String(50))
    media_path = Column(String(1024))
    message_type = Column(String(50))
    status = Column(String(50))


class WhatsAppContact(Base):
    __tablename__ = "wa_contacts"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    jid = Column(String(255), index=True)
    display_name = Column(String(512))
    phone_number = Column(String(50))
    status = Column(Text)


class WhatsAppGroup(Base):
    __tablename__ = "wa_groups"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    group_jid = Column(String(255), index=True)
    subject = Column(String(512))
    creator_jid = Column(String(255))
    creation_timestamp = Column(BigInteger)


class TelegramMessage(Base):
    __tablename__ = "tg_messages"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    message_id = Column(Integer, index=True)
    dialog_id = Column(String(255), index=True)
    sender_id = Column(Integer, index=True)
    body = Column(Text)
    timestamp = Column(BigInteger, index=True)
    media_type = Column(String(50))
    media_path = Column(String(1024))
    message_type = Column(String(50))


class TelegramContact(Base):
    __tablename__ = "tg_contacts"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    user_id = Column(Integer, index=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    username = Column(String(255))
    phone = Column(String(50))


class TelegramGroup(Base):
    __tablename__ = "tg_groups"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    group_id = Column(Integer, index=True)
    title = Column(String(512))
    username = Column(String(255))
    type = Column(String(50))


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    event_type = Column(String(50), index=True)

    source_app = Column(String(50), index=True)
    timestamp = Column(BigInteger, index=True)
    normalized_timestamp = Column(DateTime, index=True)
    entity_id = Column(String(255))
    entity_type = Column(String(50))
    description = Column(Text)
    metadata_ = Column("metadata_", JSON, default=dict)

    case = relationship("Case", back_populates="timeline_events")


class DeletedMessage(Base):
    __tablename__ = "deleted_messages"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    source_app = Column(String(50), index=True)
    chat_jid = Column(String(255))
    gap_start = Column(BigInteger)
    gap_end = Column(BigInteger)
    missing_count = Column(Integer)
    confidence_score = Column(Float)
    detection_method = Column(String(50))
    detected_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="deleted_messages")


class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    file_path = Column(String(1024))
    sha256 = Column(String(64))
    mime_type = Column(String(255))
    media_type = Column(String(50))
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    duration = Column(Float)
    exif_data = Column(JSON, default=dict)
    is_orphan = Column(Boolean, default=False)
    linked_message_id = Column(String(255))

    case = relationship("Case", back_populates="media_items")


class CorrelationEdge(Base):
    __tablename__ = "correlation_edges"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    source_type = Column(String(50))
    target_type = Column(String(50))
    source_id = Column(String(255))
    target_id = Column(String(255))
    relation_type = Column(String(50))
    metadata_ = Column("metadata_", JSON, default=dict)


class AnalysisLog(Base):
    __tablename__ = "analysis_logs"

    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    log_type = Column(String(50))
    message = Column(Text)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    action = Column(String(255))
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="activity_logs")


class ErrorLog(Base):
    """Error/exception logs for audit trail."""

    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    error_type = Column(String(255))
    message = Column(Text)
    stack_trace = Column(Text)
    endpoint = Column(String(512))
    method = Column(String(10))
    client_ip = Column(String(50))
    user_agent = Column(String(512))
    metadata_ = Column("metadata_", JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class GeneratedReport(Base):
    """In-app report history tracker for generated court-ready reports."""

    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, index=True, nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    report_type = Column(String(50), nullable=False)
    lead_analyst = Column(String(255))
    agency = Column(String(255))
    case_notes = Column(Text)
    sha256 = Column(String(64), nullable=False, index=True)
    total_pages = Column(Integer, default=1)
    size_bytes = Column(Integer, default=0)
    filename = Column(String(255), nullable=False)
    pdf_data = Column(LargeBinary, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="generated_reports")


class RecoveryRun(Base):
    """Audit record for a physical deleted message recovery run."""

    __tablename__ = "recovery_runs"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    status = Column(String(50), default="QUEUED", index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    findings_count = Column(Integer, default=0)
    wal_pages_analyzed = Column(Integer, default=0)
    freelist_pages_analyzed = Column(Integer, default=0)
    slack_spans_analyzed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    case = relationship("Case", back_populates="recovery_runs")
    findings = relationship("RecoveredFinding", back_populates="recovery_run", cascade="all, delete-orphan")


class RecoveredFinding(Base):
    """Physically carved deleted message or candidate record."""

    __tablename__ = "recovered_findings"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("recovery_runs.id"), nullable=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False, index=True)
    source_file_id = Column(Integer, ForeignKey("evidence_files.id"), nullable=True)
    source_app = Column(String(50), default="unknown", index=True)
    method = Column(String(50), nullable=False, index=True)  # wal, freelist, slack, record_reconstruction
    page_number = Column(Integer, default=0)
    byte_offset = Column(BigInteger, default=0)
    raw_payload_hash = Column(String(64), nullable=False, index=True)
    raw_payload_preview = Column(Text, nullable=True)
    message_id = Column(String(255), nullable=True)
    chat_id = Column(String(255), nullable=True, index=True)
    sender_id = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    timestamp = Column(BigInteger, nullable=True, index=True)
    media_reference = Column(String(1024), nullable=True)
    validation_status = Column(String(50), default="CANDIDATE", index=True)  # RECOVERED, PARTIALLY_RECONSTRUCTED, CANDIDATE, UNVALIDATED
    limitations = Column(JSON, default=list)
    provenance = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="recovered_findings")
    recovery_run = relationship("RecoveryRun", back_populates="findings")


class DerivedArtifact(Base):
    """
    Decrypted database, decrypted media exhibit, or reconstructed artifact
    stored directly in PostgreSQL BYTEA with parent exhibit provenance (zero disk storage).
    """

    __tablename__ = "derived_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    parent_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False, index=True)
    parent_file_id = Column(Integer, ForeignKey("evidence_files.id"), nullable=True, index=True)
    original_filename = Column(String(512), nullable=False)
    artifact_type = Column(String(50), nullable=False, index=True)  # decrypted_sqlite, decrypted_media, recovered_secret_chat
    sha256 = Column(String(64), nullable=False, index=True)
    size_bytes = Column(Integer, default=0)
    mime_type = Column(String(255), nullable=True)
    content_bytes = Column(LargeBinary, nullable=True)
    provenance = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    case = relationship("Case", back_populates="derived_artifacts")
    evidence = relationship("Evidence", back_populates="derived_artifacts")


class DecryptionOperation(Base):
    """
    Audit record for cryptographic decryption operations and derivation provenance.
    Never persists keys or passcodes.
    """

    __tablename__ = "decryption_operations"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("evidence_files.id"), nullable=True, index=True)
    format = Column(String(50), nullable=False, index=True)  # crypt12, crypt14, crypt15, sqlcipher, enc, mtproto
    status = Column(String(50), default="QUEUED", index=True)  # QUEUED, RUNNING, SUCCEEDED, FAILED
    input_sha256 = Column(String(64), nullable=False, index=True)
    output_sha256 = Column(String(64), nullable=True, index=True)
    derived_artifact_id = Column(Integer, ForeignKey("derived_artifacts.id"), nullable=True, index=True)
    parameters = Column(JSON, default=dict)  # Sanitized, non-sensitive parameters
    validation = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="decryption_operations")
    evidence = relationship("Evidence", back_populates="decryption_operations")
    derived_artifact = relationship("DerivedArtifact")


class PersonEntity(Base):
    """
    Resolved Person hypothesis cluster grouping corroborated accounts,
    phone numbers, and handles with provenance and explicit limitations.
    """

    __tablename__ = "person_entities"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    entity_uuid = Column(String(64), unique=True, index=True, nullable=False)
    label = Column(String(255), nullable=False)
    entity_type = Column(String(50), default="PERSON", index=True)
    confidence_score = Column(Float, default=1.0)
    resolution_method = Column(String(100), nullable=False)
    attributes = Column(JSON, default=dict)
    evidence_links = Column(JSON, default=list)
    limitations = Column(JSON, default=list)
    provenance = Column(JSON, default=dict)
    is_ambiguous = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    case = relationship("Case", back_populates="person_entities")


class CorrelationFinding(Base):
    """
    Stores specialized deep correlation findings:
    - Platform handover candidates
    - Perceptual media hash matches
    - Shared financial/crypto/logistical artifacts
    - Spatiotemporal rendezvous candidates
    """

    __tablename__ = "correlation_findings"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    finding_uuid = Column(String(64), unique=True, index=True, nullable=False)
    finding_type = Column(String(50), nullable=False, index=True)  # handover, media_match, shared_artifact, rendezvous
    sub_type = Column(String(50), nullable=True, index=True)       # e.g., BITCOIN, EVM, IBAN, dHash, EXIF_GPS
    confidence_score = Column(Float, default=1.0)
    details = Column(JSON, default=dict)
    evidence_ids = Column(JSON, default=list)
    limitations = Column(JSON, default=list)
    provenance = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    case = relationship("Case", back_populates="correlation_findings")