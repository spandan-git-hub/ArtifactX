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
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
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