"""
Physical Recovery Orchestrator.
Coordinates WAL parsing, freelist carving, B-tree cell slack extraction, and payload reconstruction.
"""

import binascii
import hashlib
from typing import Any, Dict, List, Optional, Tuple

from forensic.deleted.freelist_carver import FreelistCarver
from forensic.deleted.payload_decoder import (
    TelegramPayloadDecoder,
    WhatsAppPayloadDecoder,
)
from forensic.deleted.slack_carver import SlackCarver
from forensic.deleted.sqlite_record import find_candidate_records
from forensic.deleted.wal_carver import WalCarver


ALGORITHM_VERSION = "2.0.0-r2"


def make_hex_preview(data: bytes, max_bytes: int = 128) -> str:
    """Create a formatted hex + ASCII preview of carved bytes."""
    slice_data = data[:max_bytes]
    hex_str = binascii.hexlify(slice_data).decode("ascii")
    spaced_hex = " ".join(hex_str[i : i + 2] for i in range(0, len(hex_str), 2))
    ascii_chars = "".join(chr(b) if 32 <= b <= 126 else "." for b in slice_data)
    suffix = f" ... ({len(data)} bytes total)" if len(data) > max_bytes else ""
    return f"{spaced_hex}\n|{ascii_chars}|{suffix}"


class DeletedRecoveryEngine:
    """Unified engine for non-destructive SQLite physical carving."""

    def __init__(
        self,
        db_bytes: bytes,
        wal_bytes: Optional[bytes] = None,
        source_app_hint: Optional[str] = None,
        source_sha256: str = "",
        evidence_id: int = 0,
        case_id: int = 0,
    ):
        self.db_bytes = db_bytes
        self.wal_bytes = wal_bytes
        self.source_app_hint = source_app_hint or "whatsapp"
        self.source_sha256 = source_sha256 or hashlib.sha256(db_bytes).hexdigest()
        self.evidence_id = evidence_id
        self.case_id = case_id

        self.findings: List[Dict[str, Any]] = []
        self.wal_pages_analyzed = 0
        self.freelist_pages_analyzed = 0
        self.slack_spans_analyzed = 0
        self.diagnostics: List[str] = []

    def run(self) -> List[Dict[str, Any]]:
        """Run all carving passes non-destructively."""
        seen_keys = set()

        # 1. Carve WAL (if provided)
        if self.wal_bytes and len(self.wal_bytes) >= 32:
            try:
                wal_carver = WalCarver(self.wal_bytes)
                if wal_carver.parse():
                    superseded = wal_carver.get_superseded_pages()
                    all_frames = wal_carver.frames
                    self.wal_pages_analyzed = len(all_frames)

                    # Scan frames for candidate records
                    for frame in all_frames:
                        candidates = find_candidate_records(frame.data, min_columns=2)
                        for c in candidates:
                            raw_slice = c["raw_bytes"]
                            h = hashlib.sha256(raw_slice).hexdigest()
                            dedup_key = (h, frame.offset + c["offset"])
                            if dedup_key in seen_keys:
                                continue
                            seen_keys.add(dedup_key)

                            decoded = self._decode_payload(c["values"], raw_slice)
                            if decoded:
                                self.findings.append(
                                    self._format_finding(
                                        method="wal",
                                        page_number=frame.page_number,
                                        byte_offset=frame.offset + c["offset"],
                                        raw_bytes=raw_slice,
                                        decoded=decoded,
                                        extra_params={
                                            "frame_index": frame.frame_index,
                                            "is_commit": frame.commit_size > 0,
                                        },
                                    )
                                )
            except Exception as e:
                self.diagnostics.append(f"WAL carving exception: {e}")

        # 2. Carve Freelist Pages
        if len(self.db_bytes) >= 100:
            try:
                fl_carver = FreelistCarver(self.db_bytes)
                if fl_carver.parse_header():
                    fl_records = fl_carver.carve_all_freelist_pages()
                    self.freelist_pages_analyzed = len(fl_carver.freelist_pages)

                    for rec in fl_records:
                        raw_slice = rec.raw_bytes
                        h = hashlib.sha256(raw_slice).hexdigest()
                        dedup_key = (h, rec.byte_offset)
                        if dedup_key in seen_keys:
                            continue
                        seen_keys.add(dedup_key)

                        decoded = self._decode_payload(rec.values, raw_slice)
                        if decoded:
                            self.findings.append(
                                self._format_finding(
                                    method="freelist",
                                    page_number=rec.page_number,
                                    byte_offset=rec.byte_offset,
                                    raw_bytes=raw_slice,
                                    decoded=decoded,
                                    extra_params={
                                        "relative_page_offset": rec.relative_offset,
                                    },
                                )
                            )
            except Exception as e:
                self.diagnostics.append(f"Freelist carving exception: {e}")

        # 3. Carve B-Tree Page Slack and Freeblocks
        if len(self.db_bytes) >= 512:
            try:
                page_size = 4096
                if len(self.db_bytes) >= 100 and self.db_bytes.startswith(b"SQLite format 3\x00"):
                    import struct
                    raw_ps = struct.unpack(">H", self.db_bytes[16:18])[0]
                    page_size = 65536 if raw_ps == 1 else raw_ps

                slack_carver = SlackCarver(self.db_bytes, page_size=page_size)
                slack_records = slack_carver.scan_all_pages()
                self.slack_spans_analyzed = len(slack_carver.slack_spans)

                for rec in slack_records:
                    raw_slice = rec.raw_bytes
                    h = hashlib.sha256(raw_slice).hexdigest()
                    dedup_key = (h, rec.absolute_byte_offset)
                    if dedup_key in seen_keys:
                        continue
                    seen_keys.add(dedup_key)

                    decoded = self._decode_payload(rec.values, raw_slice)
                    if decoded:
                        self.findings.append(
                            self._format_finding(
                                method="slack",
                                page_number=rec.page_number,
                                byte_offset=rec.absolute_byte_offset,
                                raw_bytes=raw_slice,
                                decoded=decoded,
                                extra_params={
                                    "span_type": rec.span_type,
                                },
                            )
                        )
            except Exception as e:
                self.diagnostics.append(f"Slack carving exception: {e}")

        return self.findings

    def _decode_payload(self, values: List[Any], raw_bytes: bytes) -> Optional[Any]:
        """Try WhatsApp then Telegram decoders."""
        if self.source_app_hint == "telegram":
            dec = TelegramPayloadDecoder.decode_record(values, raw_bytes)
            if dec:
                return dec
            return WhatsAppPayloadDecoder.decode_record(values, raw_bytes)
        else:
            dec = WhatsAppPayloadDecoder.decode_record(values, raw_bytes)
            if dec:
                return dec
            return TelegramPayloadDecoder.decode_record(values, raw_bytes)

    def _format_finding(
        self,
        method: str,
        page_number: int,
        byte_offset: int,
        raw_bytes: bytes,
        decoded: Any,
        extra_params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        raw_hash = hashlib.sha256(raw_bytes).hexdigest()
        preview = make_hex_preview(raw_bytes)

        provenance = {
            "source_artifact_id": self.evidence_id,
            "source_sha256": self.source_sha256,
            "method": method,
            "algorithm_version": ALGORITHM_VERSION,
            "parameters": extra_params or {},
        }

        return {
            "case_id": self.case_id,
            "evidence_id": self.evidence_id,
            "source_sha256": self.source_sha256,
            "source_app": decoded.source_app,
            "method": method,
            "page_number": page_number,
            "byte_offset": byte_offset,
            "raw_payload_hash": raw_hash,
            "raw_payload_preview": preview,
            "message_id": decoded.message_id,
            "chat_id": decoded.chat_id,
            "sender_id": decoded.sender_id,
            "body": decoded.body,
            "timestamp": decoded.timestamp,
            "media_reference": decoded.media_reference,
            "validation_status": decoded.validation_status,
            "limitations": decoded.limitations,
            "provenance": provenance,
        }
