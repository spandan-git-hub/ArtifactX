from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class MongoModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        populate_by_name=True,
    )


class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=140)
    description: str = Field(default="", max_length=2000)
    investigator: str = Field(default="Investigator", max_length=120)


class Case(MongoModel):
    id: str
    title: str
    description: str
    investigator: str
    created_at: datetime
    status: str = "open"


class Evidence(MongoModel):
    id: str
    case_id: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime
    parser_type: str = "whatsapp_txt"
    parse_status: str
    storage_path: str
    statistics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ArtifactMessage(MongoModel):
    id: str
    case_id: str
    evidence_id: str
    timestamp: datetime | None
    sender: str | None
    content: str
    message_type: str
    raw_text: str
    flags: list[str] = Field(default_factory=list)


class TimelineEvent(MongoModel):
    id: str
    case_id: str
    evidence_id: str
    artifact_id: str
    timestamp: datetime | None
    source: str = "whatsapp"
    actor: str | None
    event_type: str
    summary: str


class AuditEvent(MongoModel):
    id: str
    case_id: str
    action: str
    actor: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    converted = dict(doc)
    if "_id" in converted:
        converted["id"] = str(converted.pop("_id"))
    return converted


def serialize_many(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialize_doc(doc) for doc in docs if doc is not None]
