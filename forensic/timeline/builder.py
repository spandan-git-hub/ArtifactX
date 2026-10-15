"""Pure forensic timeline event builder and deterministic sequencer (Rule R8, R10, R11, R18).

Pure module: no database imports, no FastAPI imports, no disk writes.
Accepts pure data dictionaries/records, normalizes timestamps with quality flags,
applies total deterministic ordering, excludes live duplicates and Tier-4 gaps,
and computes cryptographic timeline hash.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from forensic.timeline.config import TimelineConfig
from forensic.timeline.models import (
    SourceRef,
    TimelineEvent,
    TimeValue,
    compute_canonical_event_id,
    compute_timeline_hash,
)
from forensic.timeline.normalizer import (
    normalize_time_value,
    parse_exif_datetime_str,
    parse_gps_timestamp_to_utc_ms,
)


@dataclass(frozen=True)
class TimelineResult:
    """Deterministic result of timeline assembly per spec B11.2."""
    events: Tuple[TimelineEvent, ...]
    unplaced_indicators: Tuple[Dict[str, Any], ...]
    timeline_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "unplaced_indicators": list(self.unplaced_indicators),
            "timeline_hash": self.timeline_hash,
            "total_events": len(self.events),
        }


def _dict_val(item: Any, *keys: str, default: Any = None) -> Any:
    """Helper to extract value from dict or object attribute."""
    for k in keys:
        if isinstance(item, dict):
            if k in item and item[k] is not None:
                return item[k]
        elif hasattr(item, k):
            v = getattr(item, k)
            if v is not None:
                return v
    return default


class PureTimelineBuilder:
    """
    Pure builder assembling timeline events across WhatsApp, Telegram, Recovery, Media, and Ingest.
    Strictly zero DB or framework dependencies (Rule R18).
    """

    def __init__(self, config: Optional[TimelineConfig] = None):
        self.config = config or TimelineConfig()

    def build_timeline(
        self,
        evidence_records: Optional[List[Any]] = None,
        whatsapp_messages: Optional[List[Any]] = None,
        whatsapp_revocations: Optional[List[Any]] = None,
        whatsapp_edits: Optional[List[Any]] = None,
        telegram_messages: Optional[List[Any]] = None,
        recovered_records: Optional[List[Any]] = None,
        media_exif_records: Optional[List[Any]] = None,
        ingest_time_map: Optional[Dict[str, int]] = None,
    ) -> TimelineResult:
        """
        Build and deterministically order all timeline events per spec B11.1–B11.4.
        """
        evidence_records = evidence_records or []
        whatsapp_messages = whatsapp_messages or []
        whatsapp_revocations = whatsapp_revocations or []
        whatsapp_edits = whatsapp_edits or []
        telegram_messages = telegram_messages or []
        recovered_records = recovered_records or []
        media_exif_records = media_exif_records or []
        ingest_time_map = ingest_time_map or {}

        events: List[TimelineEvent] = []
        unplaced_indicators: List[Dict[str, Any]] = []

        # 1. Evidence Ingestion Events
        for ev in evidence_records:
            ev_id = _dict_val(ev, "evidence_id", "id")
            sha256 = _dict_val(ev, "sha256", "evidence_sha256") or ""
            fname = _dict_val(ev, "original_filename", "filename") or f"evidence_{ev_id}"
            app_type = _dict_val(ev, "evidence_type", default="system")
            uploaded_at = _dict_val(ev, "uploaded_at_ms", "uploaded_at", "created_at")

            raw_ts = uploaded_at
            if isinstance(uploaded_at, datetime):
                raw_ts = int(uploaded_at.replace(tzinfo=timezone.utc).timestamp() * 1000) if uploaded_at.tzinfo else int(uploaded_at.timestamp() * 1000)

            tval = normalize_time_value(
                raw=raw_ts,
                unit="ms",
                evidence_ingest_time_ms=None,
                config=self.config,
            )
            sref = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table="evidence",
                source_row_id=ev_id,
            )
            eid = compute_canonical_event_id(
                kind="system",
                evidence_sha256=sha256,
                source_table="evidence",
                row_or_offset=ev_id,
                raw_time=raw_ts,
                key_facts={"action": "evidence_ingest", "filename": fname},
            )
            event = TimelineEvent(
                event_id=eid,
                kind="system",
                app="system",
                time=tval,
                actor_ref=None,
                chat_ref=None,
                summary=f"Evidence ingested: {fname}",
                source_refs=(sref,),
                confidence_score=1.0,
                strength="deterministic",
                limitations=(),
                metadata={"filename": fname, "evidence_type": app_type, "sha256": sha256},
            )
            events.append(event)

        # 2. WhatsApp Messages (Modern schema: unit = ms)
        for msg in whatsapp_messages:
            ev_id = _dict_val(msg, "evidence_id")
            sha256 = _dict_val(msg, "evidence_sha256") or ""
            msg_id = _dict_val(msg, "message_id", "_id", "id")
            key_id = _dict_val(msg, "key_id") or f"wa_msg_{msg_id}"
            raw_ts = _dict_val(msg, "timestamp", "timestamp_ms", "received_timestamp", "received_timestamp_ms")
            chat_ref = _dict_val(msg, "chat_jid", "key_remote_jid")
            sender_ref = _dict_val(msg, "sender_jid", "participant_jid") or chat_ref
            body = _dict_val(msg, "body", "text_data") or ""
            msg_type = _dict_val(msg, "message_type", default=0)
            media_path = _dict_val(msg, "media_path", "file_path")

            ingest_ms = ingest_time_map.get(sha256)
            tval = normalize_time_value(
                raw=raw_ts,
                unit="ms",
                evidence_ingest_time_ms=ingest_ms,
                config=self.config,
            )
            sref = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table="message",
                source_row_id=msg_id,
            )
            kind = "message"
            if msg_type == 5 or _dict_val(msg, "latitude") is not None:
                kind = "location"

            summary = body if body else (f"Media: {media_path}" if media_path else f"WhatsApp message {key_id}")
            eid = compute_canonical_event_id(
                kind=kind,
                evidence_sha256=sha256,
                source_table="message",
                row_or_offset=msg_id,
                raw_time=raw_ts,
                key_facts={"chat_ref": chat_ref or "", "key_id": key_id},
            )
            event = TimelineEvent(
                event_id=eid,
                kind=kind,
                app="whatsapp",
                time=tval,
                actor_ref=sender_ref,
                chat_ref=chat_ref,
                summary=summary,
                source_refs=(sref,),
                confidence_score=1.0,
                strength="deterministic",
                limitations=(),
                metadata={
                    "key_id": key_id,
                    "message_type": msg_type,
                    "media_path": media_path,
                },
            )
            events.append(event)

        # 3. WhatsApp Revocations ("Deleted for everyone")
        for rev in whatsapp_revocations:
            ev_id = _dict_val(rev, "evidence_id")
            sha256 = _dict_val(rev, "evidence_sha256") or ""
            rev_id = _dict_val(rev, "id", "revocation_id")
            msg_id = _dict_val(rev, "message_id", "row_id")
            key_id = _dict_val(rev, "key_id") or f"rev_{msg_id}"
            chat_ref = _dict_val(rev, "chat_jid")
            rev_ts = _dict_val(rev, "revoked_timestamp", "revoked_timestamp_ms", "timestamp_ms", "timestamp")
            orig_ts = _dict_val(rev, "original_timestamp", "original_timestamp_ms")

            ingest_ms = ingest_time_map.get(sha256)
            tval = normalize_time_value(
                raw=rev_ts,
                unit="ms",
                evidence_ingest_time_ms=ingest_ms,
                config=self.config,
            )
            sref_holder = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table="message",
                source_row_id=msg_id,
            )
            sref_info = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table="message_revoked" if _dict_val(rev, "source_table") is None else _dict_val(rev, "source_table"),
                source_row_id=rev_id,
            )
            eid = compute_canonical_event_id(
                kind="revocation",
                evidence_sha256=sha256,
                source_table="message_revoked",
                row_or_offset=rev_id or msg_id,
                raw_time=rev_ts,
                key_facts={"chat_ref": chat_ref or "", "key_id": key_id},
            )
            event = TimelineEvent(
                event_id=eid,
                kind="revocation",
                app="whatsapp",
                time=tval,
                actor_ref=_dict_val(rev, "sender_jid") or chat_ref,
                chat_ref=chat_ref,
                summary=f"Message revoked ('Deleted for everyone'): {key_id}",
                source_refs=(sref_holder, sref_info),
                confidence_score=1.0,
                strength="deterministic",
                limitations=("Explicit revocation record in message store",),
                metadata={
                    "key_id": key_id,
                    "original_timestamp_ms": orig_ts,
                    "revocation_id": rev_id,
                },
            )
            events.append(event)

        # 4. WhatsApp Edits
        for edit in whatsapp_edits:
            ev_id = _dict_val(edit, "evidence_id")
            sha256 = _dict_val(edit, "evidence_sha256") or ""
            edit_id = _dict_val(edit, "id", "edit_id")
            msg_id = _dict_val(edit, "message_id", "row_id")
            key_id = _dict_val(edit, "key_id") or f"edit_{msg_id}"
            chat_ref = _dict_val(edit, "chat_jid")
            edit_ts = _dict_val(edit, "edit_timestamp", "edit_timestamp_ms", "timestamp_ms", "timestamp")

            ingest_ms = ingest_time_map.get(sha256)
            tval = normalize_time_value(
                raw=edit_ts,
                unit="ms",
                evidence_ingest_time_ms=ingest_ms,
                config=self.config,
            )
            sref_holder = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table="message",
                source_row_id=msg_id,
            )
            sref_edit = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table="message_edit_info",
                source_row_id=edit_id,
            )
            eid = compute_canonical_event_id(
                kind="edit",
                evidence_sha256=sha256,
                source_table="message_edit_info",
                row_or_offset=edit_id or msg_id,
                raw_time=edit_ts,
                key_facts={"chat_ref": chat_ref or "", "key_id": key_id},
            )
            event = TimelineEvent(
                event_id=eid,
                kind="edit",
                app="whatsapp",
                time=tval,
                actor_ref=_dict_val(edit, "sender_jid") or chat_ref,
                chat_ref=chat_ref,
                summary=f"Message edited: {key_id}",
                source_refs=(sref_holder, sref_edit),
                confidence_score=1.0,
                strength="deterministic",
                limitations=(),
                metadata={
                    "key_id": key_id,
                    "old_text": _dict_val(edit, "old_text"),
                    "new_text": _dict_val(edit, "new_text"),
                },
            )
            events.append(event)

        # 5. Telegram Messages (MTProto schema: unit = seconds)
        for msg in telegram_messages:
            ev_id = _dict_val(msg, "evidence_id")
            sha256 = _dict_val(msg, "evidence_sha256") or ""
            msg_id = _dict_val(msg, "message_id", "mid", "id")
            dialog_id = _dict_val(msg, "dialog_id")
            sender_id = _dict_val(msg, "sender_id")
            date_s = _dict_val(msg, "date_raw", "date", "date_s")
            raw_date = date_s
            unit = "s"
            if date_s is None:
                raw_ms = _dict_val(msg, "date_utc_ms", "timestamp")
                if raw_ms is not None:
                    raw_date = raw_ms
                    unit = "ms" if int(raw_ms) > 100_000_000_000 else "s"

            body = _dict_val(msg, "body", "message") or ""
            view = _dict_val(msg, "view", default="main_view")

            chat_ref = f"tg_dialog_{dialog_id}" if dialog_id else None
            actor_ref = f"tg_user_{sender_id}" if sender_id else chat_ref

            ingest_ms = ingest_time_map.get(sha256)
            tval = normalize_time_value(
                raw=raw_date,
                unit=unit,
                evidence_ingest_time_ms=ingest_ms,
                config=self.config,
            )
            sref = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table="messages_v2",
                source_row_id=msg_id,
            )
            summary = body if body else f"Telegram message {msg_id}"
            eid = compute_canonical_event_id(
                kind="message",
                evidence_sha256=sha256,
                source_table="messages_v2",
                row_or_offset=msg_id,
                raw_time=raw_date,
                key_facts={"dialog_id": dialog_id or 0, "view": view},
            )
            event = TimelineEvent(
                event_id=eid,
                kind="message",
                app="telegram",
                time=tval,
                actor_ref=actor_ref,
                chat_ref=chat_ref,
                summary=summary,
                source_refs=(sref,),
                confidence_score=1.0,
                strength="deterministic",
                limitations=(),
                metadata={"dialog_id": dialog_id, "sender_id": sender_id, "view": view},
            )
            events.append(event)

        # 6. Recovered Records (Tiers 1–3 only; Tier 4 gaps are NEVER placed on timeline; live duplicates excluded)
        for rec in recovered_records:
            tier = _dict_val(rec, "tier", default=0)
            status = _dict_val(rec, "validation_status", "status") or ""

            # Rule B11.3: Exclude live duplicates
            if status == "DUPLICATE_OF_LIVE" or _dict_val(rec, "is_duplicate_of_live", default=False):
                continue

            # Rule B11.3 / DEC-014: Tier-4 ID gaps have NO timestamp and are NEVER placed on timeline
            if tier == 4 or _dict_val(rec, "kind") == "id_gap":
                unplaced_indicators.append({
                    "kind": "id_gap",
                    "finding_id": _dict_val(rec, "finding_id"),
                    "table_name": _dict_val(rec, "table_name"),
                    "details": _dict_val(rec, "recovered_fields", default={}),
                    "confidence_score": _dict_val(rec, "confidence_score", default=0.25),
                    "strength": "weak_hint",
                    "reason": "Tier-4 primary key gaps have no determinable timestamp; excluded from timeline.",
                })
                continue

            # Valid recovered records (Tier 1, 2, 3)
            ev_id = _dict_val(rec, "evidence_id")
            sha256 = _dict_val(rec, "evidence_sha256") or ""
            finding_id = _dict_val(rec, "finding_id") or f"rec_{len(events)}"
            app_type = _dict_val(rec, "app", default="whatsapp")
            rec_fields = _dict_val(rec, "recovered_fields") or {}
            source_table = _dict_val(rec, "table_name", default="sqlite_carved")

            # Extract timestamp from recovered record's own fields
            raw_rec_ts = _dict_val(rec_fields, "timestamp", "timestamp_ms", "date", "date_s", "created_timestamp")
            # If WhatsApp -> ms; if Telegram -> s
            unit = "ms" if app_type == "whatsapp" else "s"
            ingest_ms = ingest_time_map.get(sha256)

            if raw_rec_ts is not None and str(raw_rec_ts).strip() != "":
                tval = normalize_time_value(
                    raw=raw_rec_ts,
                    unit=unit,
                    evidence_ingest_time_ms=ingest_ms,
                    config=self.config,
                )
            else:
                # PARTIAL record without decodable timestamp -> utc_ms = None, sorts last
                tval = TimeValue(
                    raw="",
                    unit="unknown",
                    utc_ms=None,
                    tz_basis="not_applicable",
                    flags=("NO_TIMESTAMP",),
                )

            sref = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table=source_table,
                source_row_id=_dict_val(rec_fields, "_id", "rowid", "id"),
                offset=_dict_val(rec, "byte_offset", "frame_index"),
            )
            strength = _dict_val(rec, "strength", default="strong")
            conf = _dict_val(rec, "confidence_score", default=0.90)
            summary_text = _dict_val(rec_fields, "text_data", "body", "message") or f"Recovered Tier-{tier} record"

            eid = compute_canonical_event_id(
                kind="recovered_record",
                evidence_sha256=sha256,
                source_table=source_table,
                row_or_offset=finding_id,
                raw_time=raw_rec_ts,
                key_facts={"tier": tier, "finding_id": finding_id},
            )
            event = TimelineEvent(
                event_id=eid,
                kind="recovered_record",
                app=app_type,
                time=tval,
                actor_ref=_dict_val(rec_fields, "sender_jid", "sender_id"),
                chat_ref=_dict_val(rec_fields, "chat_jid", "dialog_id"),
                summary=summary_text,
                source_refs=(sref,),
                confidence_score=float(conf),
                strength=strength,
                limitations=("Carved from SQLite unallocated/freelist/WAL",),
                metadata={
                    "tier": tier,
                    "finding_id": finding_id,
                    "validation_status": status,
                    "source_table": source_table,
                },
            )
            events.append(event)

        # 7. Media EXIF & GPS Records
        for media in media_exif_records:
            ev_id = _dict_val(media, "evidence_id")
            sha256 = _dict_val(media, "evidence_sha256") or ""
            fname = _dict_val(media, "filename", "media_name", "file_path") or "image.jpg"
            dt_orig = _dict_val(media, "date_time_original", "DateTimeOriginal")
            offset_orig = _dict_val(media, "offset_time_original", "OffsetTimeOriginal")
            gps_date = _dict_val(media, "gps_date_stamp", "GPSDateStamp")
            gps_time = _dict_val(media, "gps_time_stamp", "GPSTimeStamp")
            exif_type = _dict_val(media, "exif_type", default="naive_dt")

            ingest_ms = ingest_time_map.get(sha256)

            # Determine primary EXIF TimeValue
            exif_tval: Optional[TimeValue] = None
            if dt_orig and offset_orig:
                exif_tval = normalize_time_value(
                    raw=dt_orig,
                    unit="exif_offset",
                    evidence_ingest_time_ms=ingest_ms,
                    config=self.config,
                    offset_str=offset_orig,
                )
            elif dt_orig:
                exif_tval = normalize_time_value(
                    raw=dt_orig,
                    unit="exif_naive",
                    evidence_ingest_time_ms=ingest_ms,
                    config=self.config,
                )

            # Parse GPS timestamp if present
            gps_tval: Optional[TimeValue] = None
            if gps_date and gps_time:
                gps_tval = normalize_time_value(
                    raw=gps_date,
                    unit="gps_utc",
                    evidence_ingest_time_ms=ingest_ms,
                    config=self.config,
                    gps_time_tuple=gps_time,
                )

            # Rule B11.4: Check GPS vs EXIF clock disagreement
            if exif_tval and exif_tval.utc_ms is not None and gps_tval and gps_tval.utc_ms is not None:
                delta = abs(gps_tval.utc_ms - exif_tval.utc_ms)
                if delta > self.config.gps_exif_tolerance_ms:
                    # Emit CLOCK_ANOMALY indicator
                    unplaced_indicators.append({
                        "kind": "clock_anomaly",
                        "indicator": "GPS vs EXIF camera clock mismatch",
                        "evidence_sha256": sha256,
                        "filename": fname,
                        "exif_utc_ms": exif_tval.utc_ms,
                        "gps_utc_ms": gps_tval.utc_ms,
                        "delta_seconds": delta / 1000.0,
                        "strength": "weak_hint",
                        "confidence_score": 0.30,
                        "limitations": [
                            "Camera clock and GPS satellite clock disagree beyond tolerance.",
                            "Device clock/timezone change, manual time change, or unsynchronized RTC are possible causes.",
                        ],
                    })

            # Choose primary time value: GPS UTC preferred if available, else EXIF
            chosen_time = gps_tval or exif_tval or TimeValue(
                raw="",
                unit="unknown",
                utc_ms=None,
                tz_basis="not_applicable",
                flags=("NO_TIMESTAMP",),
            )

            sref = SourceRef(
                evidence_id=ev_id,
                evidence_sha256=sha256,
                source_table="media_items",
                source_row_id=_dict_val(media, "id", "media_id"),
            )
            eid = compute_canonical_event_id(
                kind="media_exif",
                evidence_sha256=sha256,
                source_table="media_items",
                row_or_offset=fname,
                raw_time=chosen_time.raw,
                key_facts={"filename": fname, "exif_type": exif_type},
            )
            event = TimelineEvent(
                event_id=eid,
                kind="media_exif",
                app="media",
                time=chosen_time,
                actor_ref=None,
                chat_ref=None,
                summary=f"Media EXIF captured: {fname}",
                source_refs=(sref,),
                confidence_score=1.0 if chosen_time.utc_ms is not None else 0.8,
                strength="deterministic" if chosen_time.tz_basis in ("utc_source", "offset_given") else "moderate",
                limitations=(
                    ("EXIF naive local time without timezone offset; UTC not determinable",)
                    if chosen_time.tz_basis == "naive_unknown_tz"
                    else ()
                ),
                metadata={
                    "filename": fname,
                    "exif_type": exif_type,
                    "gps_coords": _dict_val(media, "gps_coords"),
                },
            )
            events.append(event)

        # 8. Chat-level Analysis: DUPLICATE_TS & NON_MONOTONIC_WITH_ROWID & CLOCK_ANOMALY
        # Group events by chat_ref
        chat_groups: Dict[str, List[TimelineEvent]] = {}
        for ev in events:
            if ev.chat_ref:
                chat_groups.setdefault(ev.chat_ref, []).append(ev)

        updated_events: List[TimelineEvent] = []
        events_by_id = {e.event_id: e for e in events}

        for chat_ref, chat_evs in chat_groups.items():
            # Check DUPLICATE_TS: identical utc_ms in same chat
            ts_counts: Dict[int, int] = {}
            for ev in chat_evs:
                if ev.time.utc_ms is not None:
                    ts_counts[ev.time.utc_ms] = ts_counts.get(ev.time.utc_ms, 0) + 1

            # Check NON_MONOTONIC_WITH_ROWID within chat:
            # Sort chat events by their source_row_id if numeric
            row_sorted = []
            for ev in chat_evs:
                if ev.source_refs and ev.source_refs[0].source_row_id is not None:
                    row_id = ev.source_refs[0].source_row_id
                    if isinstance(row_id, int) or str(row_id).isdigit():
                        row_sorted.append((int(row_id), ev))

            row_sorted.sort(key=lambda x: x[0])
            non_monotonic_ids: Set[str] = set()
            for i in range(len(row_sorted) - 1):
                cur_row, cur_ev = row_sorted[i]
                nxt_row, nxt_ev = row_sorted[i + 1]
                if nxt_row > cur_row:
                    if cur_ev.time.utc_ms is not None and nxt_ev.time.utc_ms is not None:
                        # If next row has timestamp significantly earlier than current row
                        if cur_ev.time.utc_ms - nxt_ev.time.utc_ms > self.config.backward_jump_threshold_ms:
                            non_monotonic_ids.add(nxt_ev.event_id)
                            unplaced_indicators.append({
                                "kind": "clock_anomaly",
                                "indicator": "Non-monotonic timestamp jump backward",
                                "chat_ref": chat_ref,
                                "prior_row_id": cur_row,
                                "next_row_id": nxt_row,
                                "jump_ms": cur_ev.time.utc_ms - nxt_ev.time.utc_ms,
                                "strength": "weak_hint",
                                "confidence_score": 0.25,
                                "limitations": [
                                    "Device clock/timezone change, manual time change, or import/restore are possible causes.",
                                ],
                            })

            for ev in chat_evs:
                new_flags = set(ev.time.flags)
                # Check duplicate timestamp
                if ev.time.utc_ms is not None and ts_counts.get(ev.time.utc_ms, 0) >= 2:
                    new_flags.add("DUPLICATE_TS")
                # Check non-monotonic
                if ev.event_id in non_monotonic_ids:
                    new_flags.add("NON_MONOTONIC_WITH_ROWID")
                    new_flags.add("CLOCK_ANOMALY")

                if len(new_flags) != len(ev.time.flags):
                    sorted_flags = tuple(sorted(new_flags))
                    new_time = TimeValue(
                        raw=ev.time.raw,
                        unit=ev.time.unit,
                        utc_ms=ev.time.utc_ms,
                        tz_basis=ev.time.tz_basis,
                        flags=sorted_flags,
                    )
                    # Reconstruct event
                    events_by_id[ev.event_id] = TimelineEvent(
                        event_id=ev.event_id,
                        kind=ev.kind,
                        app=ev.app,
                        time=new_time,
                        actor_ref=ev.actor_ref,
                        chat_ref=ev.chat_ref,
                        summary=ev.summary,
                        source_refs=ev.source_refs,
                        confidence_score=ev.confidence_score,
                        strength=ev.strength,
                        limitations=ev.limitations,
                        metadata=ev.metadata,
                    )

        # 9. Total Deterministic Ordering (Rule R11, Spec B11.2)
        final_events = list(events_by_id.values())
        final_events.sort(key=lambda e: e.sort_key())

        # 10. Cryptographic Content Hash across canonically serialized sequence
        timeline_hash = compute_timeline_hash(final_events)

        return TimelineResult(
            events=tuple(final_events),
            unplaced_indicators=tuple(unplaced_indicators),
            timeline_hash=timeline_hash,
        )