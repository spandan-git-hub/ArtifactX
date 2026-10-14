"""Ground-truth dataset manifest schema and data structures.

Follows master.md R1, R11, R14, and 02_GROUND_TRUTH_DATASETS.md §5.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DatasetFileInfo:
    path: str
    sha256: str
    size: int


@dataclass
class WAMessageEntry:
    row_id: int
    key_id: str
    chat_jid: str
    sender_jid: str
    from_me: int
    ts_raw: int
    ts_utc_ms: int
    type: str                  # text, image, audio, location, revoked, etc.
    body: Optional[str]
    media_ref: Optional[str] = None
    quoted_of: Optional[str] = None
    flags: List[str] = field(default_factory=list)


@dataclass
class WADeletionEntry:
    case_id: str
    method: str                # revoked, freelist_deleted, slack_deleted, wal_resident, vacuumed_control, secure_delete_control, benign_gap
    expected_recoverable: bool
    expected_tier: str         # tier_1, tier_2, tier_3, tier_4, unrecoverable
    marker: str
    original_message_row_id: Optional[int] = None
    original_key_id: Optional[str] = None
    original_body: Optional[str] = None
    byte_offsets: List[int] = field(default_factory=list)
    page_numbers: List[int] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class WAEditEntry:
    message_row_id: int
    original_key_id: str
    edited_ts: int
    original_body: str
    edited_body: str


@dataclass
class WAContactEntry:
    jid: str
    display_name: str
    phone_number: str
    is_group: bool = False


@dataclass
class WAChatEntry:
    chat_jid: str
    subject: Optional[str]
    is_group: bool
    participant_jids: List[str]
    message_count: int


@dataclass
class DatasetManifest:
    dataset_id: str
    variant: str               # dev | holdout
    seed: int
    generator_version: str
    origin: str                # "synthetic"
    created_by_tool_versions: Dict[str, str]
    files: List[DatasetFileInfo]
    whatsapp: Dict[str, Any]
    telegram: Optional[Dict[str, Any]] = None
    shared_entities: List[Dict[str, Any]] = field(default_factory=list)
    decoys: List[Dict[str, Any]] = field(default_factory=list)
    controls: List[Dict[str, Any]] = field(default_factory=list)
    encryption: Optional[Dict[str, Any]] = None
    modelled_vs_observed: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to standard python dict."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert manifest to deterministic JSON string (sorted keys)."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)

    def save(self, destination: Path) -> None:
        """Write manifest.json deterministically to disk."""
        destination.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DatasetManifest:
        files = [DatasetFileInfo(**f) for f in data.get("files", [])]
        return cls(
            dataset_id=data["dataset_id"],
            variant=data["variant"],
            seed=data["seed"],
            generator_version=data["generator_version"],
            origin=data["origin"],
            created_by_tool_versions=data["created_by_tool_versions"],
            files=files,
            whatsapp=data.get("whatsapp", {}),
            telegram=data.get("telegram"),
            shared_entities=data.get("shared_entities", []),
            decoys=data.get("decoys", []),
            controls=data.get("controls", []),
            encryption=data.get("encryption"),
            modelled_vs_observed=data.get("modelled_vs_observed", {}),
        )

    @classmethod
    def load(cls, manifest_path: Path) -> DatasetManifest:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return cls.from_dict(data)
