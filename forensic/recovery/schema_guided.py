"""
Schema-guided record decoder for SQLite physical carving (spec B10.3, master.md R7, R8, R12).

Accepts/rejects candidate records based on application table schemas:
- WhatsApp modern 'message' / legacy 'messages'
- Telegram 'messages_v2' with MTProto TL blob deserialization

Guarantees:
- Zero disk writes (R4)
- Untrusted-input hardening: step budget per page, boundary checks (R12)
- Rejection tracking (invalid_rejected count) for false-positive reporting
- Unparsed blob fallback for Telegram without dropping or guessing
"""

from __future__ import annotations

import binascii
import hashlib
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from forensic.common.contracts import Provenance
from forensic.common.hashing import deterministic_finding_id, sha256_hex
from forensic.recovery.models import RecoveryFinding, ValidationStatus
from forensic.sqlite.constants import TEXT_ENCODING_UTF8
from forensic.sqlite.exceptions import CorruptPage, SQLiteForensicsError
from forensic.sqlite.record import (
    DecodedRecord,
    decode_record_detailed,
    decode_varint,
)
from forensic.telegram.tl.reader import TLError, TLReader
from forensic.telegram.tl.registry import build_supported_registry

# Lazy-loaded singleton for Telegram TL constructor registry
_TG_REGISTRY: Optional[Dict[int, Callable[[TLReader], Any]]] = None


def get_tg_registry() -> Dict[int, Callable[[TLReader], Any]]:
    global _TG_REGISTRY
    if _TG_REGISTRY is None:
        _TG_REGISTRY = build_supported_registry()
    return _TG_REGISTRY


class SchemaGuidedDecoder:
    """
    Schema-guided decoder scanning byte buffers (pages, spans, freeblocks).
    Evaluates candidate cells against WhatsApp and Telegram schema patterns.
    """

    def __init__(
        self,
        app_hint: str = "whatsapp",
        evidence_id: str = "0",
        evidence_sha256: str = "",
        max_steps_per_page: int = 25000,
    ):
        self.app_hint = (app_hint or "whatsapp").lower()
        self.evidence_id = evidence_id
        self.evidence_sha256 = evidence_sha256
        self.max_steps_per_page = max_steps_per_page
        self.invalid_rejected_count = 0
        self.warnings: List[str] = []

    def scan_buffer(
        self,
        buffer: bytes,
        page_no: int,
        base_offset: int,
        kind: str,
        tier: int = 3,
        source_table_hint: Optional[str] = None,
    ) -> List[RecoveryFinding]:
        """
        Scan a byte buffer (free page, freelist leaf, or page slack span) for candidate records.
        """
        findings: List[RecoveryFinding] = []
        buf_len = len(buffer)
        if buf_len < 16:
            return findings

        steps = 0
        off = 0
        seen_payload_hashes: Set[str] = set()

        while off < buf_len - 15:
            steps += 1
            if steps > self.max_steps_per_page:
                self.warnings.append(
                    f"Page {page_no} exceeded step budget ({self.max_steps_per_page}); partial results retained."
                )
                break

            candidate = self._try_decode_at_offset(
                buffer=buffer,
                offset=off,
                page_no=page_no,
                base_offset=base_offset,
                kind=kind,
                tier=tier,
                source_table_hint=source_table_hint,
            )

            if candidate is not None:
                # Advance past this record
                if candidate.raw_payload_hash not in seen_payload_hashes:
                    seen_payload_hashes.add(candidate.raw_payload_hash)
                    findings.append(candidate)
                # Skip forward by at least candidate's payload or 8 bytes
                consumed = candidate.recovered_fields.get("_consumed_bytes", 8)
                off += max(1, consumed)
            else:
                off += 1

        return findings

    def _try_decode_at_offset(
        self,
        buffer: bytes,
        offset: int,
        page_no: int,
        base_offset: int,
        kind: str,
        tier: int,
        source_table_hint: Optional[str],
    ) -> Optional[RecoveryFinding]:
        """Attempt to decode a valid candidate cell or record header at a given byte offset."""
        buf_len = len(buffer)
        abs_byte_offset = base_offset + offset

        # Mode A: Standard B-tree Leaf Cell [payload_size varint, rowid varint, record_header, values]
        cand_a = self._try_decode_cell(
            buffer=buffer,
            offset=offset,
            page_no=page_no,
            abs_byte_offset=abs_byte_offset,
            kind=kind,
            tier=tier,
            source_table_hint=source_table_hint,
        )
        if cand_a is not None:
            return cand_a

        # Mode B: Direct record header [record_header, values] (e.g. inside freeblock where varints were overwritten)
        cand_b = self._try_decode_record_direct(
            buffer=buffer,
            offset=offset,
            page_no=page_no,
            abs_byte_offset=abs_byte_offset,
            kind=kind,
            tier=tier,
            source_table_hint=source_table_hint,
        )
        return cand_b

    def _try_decode_cell(
        self,
        buffer: bytes,
        offset: int,
        page_no: int,
        abs_byte_offset: int,
        kind: str,
        tier: int,
        source_table_hint: Optional[str],
    ) -> Optional[RecoveryFinding]:
        buf_len = len(buffer)
        try:
            plen, c1 = decode_varint(buffer, offset)
            if plen < 12 or plen > 65536 or offset + c1 >= buf_len:
                return None

            rowid, c2 = decode_varint(buffer, offset + c1)
            payload_start = offset + c1 + c2
            if payload_start >= buf_len:
                return None

            # Check if payload fits in buffer or is partially available
            available_payload_len = min(plen, buf_len - payload_start)
            if available_payload_len < 8:
                return None

            payload_bytes = buffer[payload_start : payload_start + available_payload_len]
            is_partial = available_payload_len < plen

            return self._match_and_build_finding(
                payload_bytes=payload_bytes,
                rowid=rowid,
                page_no=page_no,
                abs_byte_offset=abs_byte_offset,
                kind=kind,
                tier=tier,
                source_table_hint=source_table_hint,
                is_partial=is_partial,
                consumed_bytes=c1 + c2 + available_payload_len,
            )
        except Exception:
            return None

    def _try_decode_record_direct(
        self,
        buffer: bytes,
        offset: int,
        page_no: int,
        abs_byte_offset: int,
        kind: str,
        tier: int,
        source_table_hint: Optional[str],
    ) -> Optional[RecoveryFinding]:
        buf_len = len(buffer)
        try:
            hdr_len, c = decode_varint(buffer, offset)
            # Record header length must be between c+1 and 100 bytes
            if hdr_len <= c or hdr_len > 120 or offset + hdr_len > buf_len:
                return None

            payload_bytes = buffer[offset :]
            return self._match_and_build_finding(
                payload_bytes=payload_bytes,
                rowid=None,
                page_no=page_no,
                abs_byte_offset=abs_byte_offset,
                kind=kind,
                tier=tier,
                source_table_hint=source_table_hint,
                is_partial=True,
                consumed_bytes=hdr_len,
            )
        except Exception:
            return None

    def _match_and_build_finding(
        self,
        payload_bytes: bytes,
        rowid: Optional[int],
        page_no: int,
        abs_byte_offset: int,
        kind: str,
        tier: int,
        source_table_hint: Optional[str],
        is_partial: bool,
        consumed_bytes: int,
    ) -> Optional[RecoveryFinding]:
        """Evaluate candidate payload against WhatsApp and Telegram schemas."""
        try:
            dec = decode_record_detailed(payload_bytes, text_encoding=TEXT_ENCODING_UTF8)
        except Exception:
            self.invalid_rejected_count += 1
            return None

        vals = dec.values
        num_cols = len(vals)

        # We evaluate matching based on app hint
        if "telegram" in self.app_hint or "tg" in self.app_hint:
            finding = self._evaluate_telegram(
                vals=vals,
                dec=dec,
                rowid=rowid,
                page_no=page_no,
                abs_byte_offset=abs_byte_offset,
                kind=kind,
                tier=tier,
                source_table_hint=source_table_hint,
                is_partial=is_partial,
                consumed_bytes=consumed_bytes,
            )
            if finding:
                return finding
        else:
            finding = self._evaluate_whatsapp(
                vals=vals,
                dec=dec,
                rowid=rowid,
                page_no=page_no,
                abs_byte_offset=abs_byte_offset,
                kind=kind,
                tier=tier,
                source_table_hint=source_table_hint,
                is_partial=is_partial,
                consumed_bytes=consumed_bytes,
            )
            if finding:
                return finding

        self.invalid_rejected_count += 1
        return None

    def _evaluate_whatsapp(
        self,
        vals: List[Any],
        dec: DecodedRecord,
        rowid: Optional[int],
        page_no: int,
        abs_byte_offset: int,
        kind: str,
        tier: int,
        source_table_hint: Optional[str],
        is_partial: bool,
        consumed_bytes: int,
    ) -> Optional[RecoveryFinding]:
        num_cols = len(vals)
        # WhatsApp modern 'message' has ~18-22 columns; legacy 'messages' has ~15-20 columns
        if num_cols < 14:
            return None

        # Schema match pattern for modern 'message':
        # col 0: None or int (_id)
        # col 1: int (chat_row_id)
        # col 2: int (from_me in (0, 1))
        # col 3 or 4: str (key_id, len >= 6)
        # col 11: int (timestamp ms)
        # col 15: Optional[str] (text_data)
        has_key_id = (
            (len(vals) > 3 and isinstance(vals[3], str) and len(vals[3]) >= 6)
            or (len(vals) > 4 and isinstance(vals[4], str) and len(vals[4]) >= 6)
        )
        is_modern = (
            (vals[0] is None or isinstance(vals[0], int))
            and isinstance(vals[1], int)
            and vals[2] in (0, 1)
            and has_key_id
        )

        # Check legacy 'messages':
        # col 1: remote_jid (contains '@')
        # col 2: from_me (0 or 1)
        # col 3: key_id
        is_legacy = (
            isinstance(vals[1], str)
            and "@" in vals[1]
            and vals[2] in (0, 1)
            and isinstance(vals[3], str)
            and len(vals[3]) >= 6
        )

        if not (is_modern or is_legacy):
            return None

        # Verify timestamp plausibility
        ts_ms: Optional[int] = None
        text_body: Optional[str] = None
        key_id = ""
        chat_id: Optional[str] = None

        if is_modern:
            # Pick best key_id candidate between col 3 and col 4
            cand3 = vals[3] if len(vals) > 3 and isinstance(vals[3], str) else ""
            cand4 = vals[4] if len(vals) > 4 and isinstance(vals[4], str) else ""
            if cand4.startswith("KEY_") or len(cand4) > len(cand3):
                key_id = cand4
            else:
                key_id = cand3 or cand4

            if len(vals) > 11 and isinstance(vals[11], int) and vals[11] > 1000000000000:
                ts_ms = vals[11]
            if len(vals) > 15 and isinstance(vals[15], str):
                text_body = vals[15]
            chat_id = str(vals[1])
        else:
            key_id = str(vals[3])
            if len(vals) > 7 and isinstance(vals[7], int) and vals[7] > 1000000000000:
                ts_ms = vals[7]
            if len(vals) > 6 and isinstance(vals[6], str):
                text_body = vals[6]
            chat_id = str(vals[1])

        # If key_id contains unprintable control characters, reject
        if not key_id.isprintable():
            return None

        val_status: ValidationStatus = "PARTIAL" if (is_partial or dec.has_encoding_errors) else "FULL_RECORD_VALID"
        limitations: List[str] = []
        if is_partial:
            limitations.append("record payload truncated or carved from fragmented unallocated space")
        if rowid is None:
            limitations.append("cell rowid varint was overwritten by intra-page freeblock pointer")

        # Deterministic finding ID
        table_name = source_table_hint or ("message" if is_modern else "messages")
        fid = deterministic_finding_id(
            method=f"tier{tier}_wa_{kind}",
            evidence_sha256=self.evidence_sha256,
            source_table=table_name,
            row_or_offset=abs_byte_offset,
            key_facts={"key_id": key_id, "rowid": rowid or 0},
        )

        raw_hash = sha256_hex(key_id.encode("utf-8") + (text_body.encode("utf-8") if text_body else b""))
        raw_preview = f"WA CARVED key_id={key_id} rowid={rowid} chat={chat_id}\nText: {(text_body or '')[:100]}"

        recovered_fields = {
            "key_id": key_id,
            "chat_id": chat_id,
            "row_id": rowid,
            "from_me": vals[2],
            "timestamp": ts_ms,
            "body": text_body,
            "_consumed_bytes": consumed_bytes,
        }

        return RecoveryFinding(
            finding_id=fid,
            confidence_score=0.90 if val_status == "FULL_RECORD_VALID" else 0.70,
            strength="strong" if val_status == "FULL_RECORD_VALID" else "moderate",
            limitations=tuple(limitations),
            provenance=Provenance(
                evidence_id=self.evidence_id,
                evidence_sha256=self.evidence_sha256,
                source_table=table_name,
                row_id=rowid,
                page_no=page_no,
                byte_offset=abs_byte_offset,
                method=f"tier{tier}_wa_{kind}",
            ),
            tier=tier,
            kind=kind,
            validation_status=val_status,
            table_name=table_name,
            row_id=rowid,
            page_no=page_no,
            byte_offset=abs_byte_offset,
            view="main_view",
            recovered_fields=recovered_fields,
            raw_payload_hash=raw_hash,
            raw_payload_preview=raw_preview,
        )

    def _evaluate_telegram(
        self,
        vals: List[Any],
        dec: DecodedRecord,
        rowid: Optional[int],
        page_no: int,
        abs_byte_offset: int,
        kind: str,
        tier: int,
        source_table_hint: Optional[str],
        is_partial: bool,
        consumed_bytes: int,
    ) -> Optional[RecoveryFinding]:
        num_cols = len(vals)
        # Telegram messages_v2 has ~18-20 columns
        if num_cols < 6:
            return None

        # Schema match pattern for messages_v2:
        # col 0: int (mid > 0)
        # col 1: int (uid)
        # col 4: int (date epoch seconds)
        # col 5: bytes (data BLOB, serialized TL)
        if not (
            isinstance(vals[0], int)
            and vals[0] > 0
            and isinstance(vals[1], int)
            and isinstance(vals[4], int)
            and vals[4] > 1000000000
            and isinstance(vals[5], (bytes, bytearray, memoryview))
            and len(vals[5]) >= 4
        ):
            return None

        mid = vals[0]
        uid = vals[1]
        date_s = vals[4]
        blob = bytes(vals[5])

        # Attempt TL deserialization of data blob
        reg = get_tg_registry()
        message_text: Optional[str] = None
        tl_parsed = False
        limitations: List[str] = []

        try:
            reader = TLReader(blob, registry=reg)
            obj = reader.read_object()
            message_text = getattr(obj, "message", None) or getattr(obj, "action_text", None)
            tl_parsed = True
        except (TLError, Exception) as exc:
            # Honest UNPARSED_BLOB fallback per B9.3 & B10.3
            limitations.append(f"TL blob deserialization incomplete ({type(exc).__name__}); unparsed blob retained")
            tl_parsed = False

        val_status: ValidationStatus = "FULL_RECORD_VALID" if (tl_parsed and not is_partial) else "PARTIAL"
        if is_partial:
            limitations.append("record carved from intra-page slack or freelist fragment")

        table_name = source_table_hint or "messages_v2"
        fid = deterministic_finding_id(
            method=f"tier{tier}_tg_{kind}",
            evidence_sha256=self.evidence_sha256,
            source_table=table_name,
            row_or_offset=abs_byte_offset,
            key_facts={"mid": mid, "uid": uid},
        )

        raw_hash = sha256_hex(blob)
        raw_preview = f"TG CARVED mid={mid} uid={uid} date={date_s}\nText: {(message_text or '')[:100]}"

        recovered_fields = {
            "mid": mid,
            "uid": uid,
            "row_id": rowid or mid,
            "date": date_s,
            "timestamp": date_s * 1000 if date_s else None,
            "body": message_text,
            "tl_parsed": tl_parsed,
            "raw_blob_len": len(blob),
            "_consumed_bytes": consumed_bytes,
        }

        return RecoveryFinding(
            finding_id=fid,
            confidence_score=0.90 if val_status == "FULL_RECORD_VALID" else 0.70,
            strength="strong" if val_status == "FULL_RECORD_VALID" else "moderate",
            limitations=tuple(limitations),
            provenance=Provenance(
                evidence_id=self.evidence_id,
                evidence_sha256=self.evidence_sha256,
                source_table=table_name,
                row_id=rowid or mid,
                page_no=page_no,
                byte_offset=abs_byte_offset,
                method=f"tier{tier}_tg_{kind}",
            ),
            tier=tier,
            kind=kind,
            validation_status=val_status,
            table_name=table_name,
            row_id=rowid or mid,
            page_no=page_no,
            byte_offset=abs_byte_offset,
            view="main_view",
            recovered_fields=recovered_fields,
            raw_payload_hash=raw_hash,
            raw_payload_preview=raw_preview,
        )
