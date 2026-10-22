"""
Pure forensic parser for WhatsApp msgstore.db and wa.db (spec B7.0–B7.4).
Zero-disk read-only operations (master.md R4, R12, R18):
Takes bytes in, yields frozen dataclasses with complete forensic provenance.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from forensic.common.contracts import Provenance
from forensic.common.hashing import deterministic_finding_id, sha256_hex
from forensic.common.sqlite_open import open_sqlite_ro, quote_ident
from forensic.whatsapp.models import (
    SchemaFamily,
    UnsupportedSchemaError,
    WAChat,
    WAContact,
    WAEdit,
    WAGroupParticipant,
    WALocationRef,
    WAMediaRef,
    WAMessage,
    WAQuotedRef,
    WARevocation,
)
from forensic.whatsapp.schema import detect_wa_schema

# Verified modern WhatsApp message type code mapping
WA_MESSAGE_TYPE_MAP: Dict[int, str] = {
    0: "text",
    1: "image",
    2: "audio",
    3: "video",
    4: "contact",
    5: "location",
    7: "system",
    8: "document",
    9: "call",
    10: "missed_call",
    12: "revoked",
    15: "sticker",
}


@dataclass(frozen=True)
class WAParseResult:
    """Forensic parse output container."""
    schema_family: SchemaFamily
    messages: Tuple[WAMessage, ...]
    chats: Tuple[WAChat, ...]
    contacts: Tuple[WAContact, ...]
    group_participants: Tuple[WAGroupParticipant, ...]
    revocations: Tuple[WARevocation, ...]
    edits: Tuple[WAEdit, ...]
    limitations: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_family": self.schema_family.to_dict(),
            "messages": [m.to_dict() for m in self.messages],
            "chats": [c.to_dict() for c in self.chats],
            "contacts": [c.to_dict() for c in self.contacts],
            "group_participants": [p.to_dict() for p in self.group_participants],
            "revocations": [r.to_dict() for r in self.revocations],
            "edits": [e.to_dict() for e in self.edits],
            "limitations": list(self.limitations),
        }


class WhatsAppParser:
    """Pure forensic parser for WhatsApp msgstore.db and optional wa.db."""

    def __init__(
        self,
        msgstore_source: Union[bytes, str],
        evidence_id: str,
        evidence_sha256: Optional[str] = None,
        wa_db_source: Optional[Union[bytes, str]] = None,
        derived_from_artifact_id: Optional[str] = None,
    ):
        self.msgstore_source = msgstore_source
        self.evidence_id = str(evidence_id)
        if evidence_sha256:
            self.evidence_sha256 = evidence_sha256
        elif isinstance(msgstore_source, bytes):
            self.evidence_sha256 = sha256_hex(msgstore_source)
        else:
            self.evidence_sha256 = "unknown"
        self.wa_db_source = wa_db_source
        self.derived_from_artifact_id = derived_from_artifact_id

    def parse(self) -> WAParseResult:
        """Parse msgstore.db and wa.db into validated forensic dataclasses."""
        conn = open_sqlite_ro(self.msgstore_source)
        try:
            schema = detect_wa_schema(conn)
            if schema.family == "modern":
                return self._parse_modern(conn, schema)
            elif schema.family == "legacy":
                return self._parse_legacy(conn, schema)
            else:
                raise UnsupportedSchemaError(
                    f"Unknown schema family: {schema.family}",
                    tables_seen=set(schema.tables),
                )
        finally:
            conn.close()

    def _parse_modern(self, conn: sqlite3.Connection, schema: SchemaFamily) -> WAParseResult:
        cursor = conn.cursor()
        limitations: List[str] = []

        # ---------------------------------------------------------------------
        # 1. Parse JIDs table
        # ---------------------------------------------------------------------
        cursor.execute("SELECT _id, user, server, raw_string, type FROM jid")
        jid_rows = cursor.fetchall()
        
        jids_by_id: Dict[int, Dict[str, Any]] = {}
        primary_user_jid: Optional[str] = None

        for row in jid_rows:
            row_id, user, server, raw_string, jid_type = row
            raw = raw_string or (f"{user}@{server}" if user and server else str(row_id))
            jids_by_id[row_id] = {
                "id": row_id,
                "user": user,
                "server": server,
                "raw_string": raw,
                "type": jid_type,
            }
            # Identify primary user if row_id == 1 and server is standard
            if row_id == 1 and server == "s.whatsapp.net":
                primary_user_jid = raw

        # ---------------------------------------------------------------------
        # 2. Parse Contacts (from wa.db if provided, else inferred from jid)
        # ---------------------------------------------------------------------
        contacts_list: List[WAContact] = []
        contact_names_by_jid: Dict[str, str] = {}

        if self.wa_db_source:
            try:
                wa_conn = open_sqlite_ro(self.wa_db_source)
                try:
                    wa_cursor = wa_conn.cursor()
                    wa_cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='wa_contacts'"
                    )
                    if wa_cursor.fetchone():
                        wa_cursor.execute(
                            "SELECT _id, jid, display_name, number, status FROM wa_contacts"
                        )
                        for c_row in wa_cursor.fetchall():
                            c_id, c_jid, c_name, c_num, c_status = c_row
                            disp_name = c_name or c_num or c_jid
                            contact_names_by_jid[c_jid] = disp_name
                            contacts_list.append(
                                WAContact(
                                    jid=c_jid,
                                    display_name=disp_name,
                                    phone_number=c_num,
                                    is_group=c_jid.endswith("@g.us"),
                                    source="wa_contacts",
                                    provenance=Provenance(
                                        evidence_id=self.evidence_id,
                                        evidence_sha256=self.evidence_sha256,
                                        source_table="wa_contacts",
                                        row_id=c_id,
                                        method="sqlite_wa_contacts",
                                        derived_from_artifact_id=self.derived_from_artifact_id,
                                    ),
                                )
                            )
                finally:
                    wa_conn.close()
            except Exception as e:
                limitations.append(f"wa.db supplied but could not be parsed: {e}")

        # If wa.db did not supply contacts or was absent, infer minimal from jid table
        if not contacts_list:
            limitations.append("Display names unavailable: wa.db not provided; contacts inferred from jid table.")
            for j_info in jids_by_id.values():
                raw = j_info["raw_string"]
                srv = j_info["server"]
                usr = j_info["user"]
                is_grp = (srv == "g.us")
                phone = usr if srv == "s.whatsapp.net" else None
                disp = usr or raw
                contact_names_by_jid[raw] = disp
                contacts_list.append(
                    WAContact(
                        jid=raw,
                        display_name=disp,
                        phone_number=phone,
                        is_group=is_grp,
                        source="jid_inferred",
                        provenance=Provenance(
                            evidence_id=self.evidence_id,
                            evidence_sha256=self.evidence_sha256,
                            source_table="jid",
                            row_id=j_info["id"],
                            method="sqlite_jid_inferred",
                            derived_from_artifact_id=self.derived_from_artifact_id,
                        ),
                    )
                )

        # ---------------------------------------------------------------------
        # 3. Parse Group Participants
        # ---------------------------------------------------------------------
        group_participants: List[WAGroupParticipant] = []
        participants_by_group_jid: Dict[str, List[str]] = {}

        if schema.capabilities.get("has_group_participants"):
            try:
                # Find the most suitable group participant table
                gp_candidate = None
                for t in schema.tables:
                    if t.startswith("group_participant"):
                        cols = set(schema.columns.get(t, ()))
                        if {"group_jid_row_id", "user_jid_row_id"}.issubset(cols):
                            gp_candidate = (t, "row_ids")
                            break
                        elif {"gjid", "jid"}.issubset(cols):
                            gp_candidate = (t, "jids")
                
                if gp_candidate:
                    gp_table, mode = gp_candidate
                    quoted_gp = quote_ident(gp_table)
                    if mode == "row_ids":
                        cursor.execute(f"SELECT _id, group_jid_row_id, user_jid_row_id, rank FROM {quoted_gp}")
                        for gp_row in cursor.fetchall():
                            gp_id, g_jid_id, u_jid_id, rank = gp_row
                            g_str = jids_by_id.get(g_jid_id, {}).get("raw_string", str(g_jid_id))
                            u_str = jids_by_id.get(u_jid_id, {}).get("raw_string", str(u_jid_id))
                            if g_str not in participants_by_group_jid:
                                participants_by_group_jid[g_str] = []
                            participants_by_group_jid[g_str].append(u_str)

                            group_participants.append(
                                WAGroupParticipant(
                                    group_jid=g_str,
                                    user_jid=u_str,
                                    rank=rank or 0,
                                    provenance=Provenance(
                                        evidence_id=self.evidence_id,
                                        evidence_sha256=self.evidence_sha256,
                                        source_table=gp_table,
                                        row_id=gp_id,
                                        method="sqlite_group_participants",
                                        derived_from_artifact_id=self.derived_from_artifact_id,
                                    ),
                                )
                            )
                    elif mode == "jids":
                        cols = set(schema.columns.get(gp_table, ()))
                        rank_col = "admin" if "admin" in cols else ("rank" if "rank" in cols else "0")
                        cursor.execute(f"SELECT _id, gjid, jid, {rank_col} FROM {quoted_gp}")
                        for gp_row in cursor.fetchall():
                            gp_id, g_val, u_val, rank_val = gp_row
                            g_str = str(g_val or "")
                            u_str = str(u_val or "")
                            if g_str not in participants_by_group_jid:
                                participants_by_group_jid[g_str] = []
                            participants_by_group_jid[g_str].append(u_str)

                            group_participants.append(
                                WAGroupParticipant(
                                    group_jid=g_str,
                                    user_jid=u_str,
                                    rank=rank_val if isinstance(rank_val, int) else 0,
                                    provenance=Provenance(
                                        evidence_id=self.evidence_id,
                                        evidence_sha256=self.evidence_sha256,
                                        source_table=gp_table,
                                        row_id=gp_id,
                                        method="sqlite_group_participants",
                                        derived_from_artifact_id=self.derived_from_artifact_id,
                                    ),
                                )
                            )
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 4. Parse Chats
        # ---------------------------------------------------------------------
        cursor.execute(
            """
            SELECT c._id, c.jid_row_id, c.hidden, c.subject, c.last_message_row_id
            FROM chat c
            ORDER BY c._id ASC
            """
        )
        chat_rows = cursor.fetchall()
        chats_list: List[WAChat] = []
        chats_by_id: Dict[int, Dict[str, Any]] = {}

        for c_row in chat_rows:
            c_id, jid_row_id, hidden, subject, last_msg_id = c_row
            j_info = jids_by_id.get(jid_row_id, {})
            chat_jid_str = j_info.get("raw_string", str(jid_row_id))
            srv = j_info.get("server", "")
            is_grp = (srv == "g.us") or (subject is not None)

            # Determine participant list
            if is_grp:
                parts = tuple(participants_by_group_jid.get(chat_jid_str, []))
            else:
                parts_list = []
                if primary_user_jid:
                    parts_list.append(primary_user_jid)
                if chat_jid_str != primary_user_jid:
                    parts_list.append(chat_jid_str)
                parts = tuple(parts_list)

            chat_obj = WAChat(
                chat_row_id=c_id,
                chat_jid=chat_jid_str,
                subject=subject,
                is_group=is_grp,
                hidden=hidden or 0,
                archived=0,
                last_message_row_id=last_msg_id,
                participant_jids=parts,
                provenance=Provenance(
                    evidence_id=self.evidence_id,
                    evidence_sha256=self.evidence_sha256,
                    source_table="chat",
                    row_id=c_id,
                    method="sqlite_chat",
                    derived_from_artifact_id=self.derived_from_artifact_id,
                ),
            )
            chats_list.append(chat_obj)
            chats_by_id[c_id] = {
                "chat_jid": chat_jid_str,
                "is_group": is_grp,
                "subject": subject,
            }

        # ---------------------------------------------------------------------
        # 5. Parse Auxiliary Tables (media, quoted, location, revoked, edits)
        # ---------------------------------------------------------------------
        media_by_msg_id: Dict[int, WAMediaRef] = {}
        if schema.capabilities.get("has_message_media"):
            try:
                mm_cols = set(schema.columns.get("message_media", ()))
                width_col = "media_width" if "media_width" in mm_cols else ("width" if "width" in mm_cols else "NULL")
                height_col = "media_height" if "media_height" in mm_cols else ("height" if "height" in mm_cols else "NULL")
                dur_col = "media_duration" if "media_duration" in mm_cols else ("duration" if "duration" in mm_cols else "NULL")
                cursor.execute(
                    f"""
                    SELECT message_row_id, file_path, file_size, media_name, mime_type,
                           file_hash, {width_col}, {height_col}, {dur_col}
                    FROM message_media
                    """
                )
                for m_row in cursor.fetchall():
                    m_row_id, fp, fsz, mn, mt, fh, mw, mh, md = m_row
                    media_by_msg_id[m_row_id] = WAMediaRef(
                        file_path=fp,
                        mime_type=mt,
                        file_size=fsz,
                        media_name=mn,
                        width=mw,
                        height=mh,
                        duration=md,
                        file_hash=fh,
                        media_key_present=False,  # Keys are radioactive (R5)
                        media_missing=False,
                    )
            except Exception:
                pass

        quoted_by_msg_id: Dict[int, WAQuotedRef] = {}
        if schema.capabilities.get("has_message_quoted"):
            try:
                mq_cols = set(schema.columns.get("message_quoted", ()))
                parent_key_col = "parent_key_id" if "parent_key_id" in mq_cols else "NULL"
                sender_col = "sender_jid_row_id" if "sender_jid_row_id" in mq_cols else "NULL"
                text_col = "text_data" if "text_data" in mq_cols else "NULL"
                cursor.execute(
                    f"""
                    SELECT message_row_id, key_id, {parent_key_col}, {sender_col},
                           timestamp, message_type, {text_col}
                    FROM message_quoted
                    """
                )
                for q_row in cursor.fetchall():
                    q_row_id, q_key_id, parent_key, q_sender_id, q_ts, q_type, q_text = q_row
                    q_sender_str = jids_by_id.get(q_sender_id, {}).get("raw_string") if q_sender_id else None
                    quoted_by_msg_id[q_row_id] = WAQuotedRef(
                        quoted_row_id=q_row_id,
                        key_id=q_key_id,
                        parent_key_id=parent_key,
                        sender_jid=q_sender_str,
                        timestamp_raw=q_ts,
                        message_type=q_type,
                        text_data=q_text,
                    )
            except Exception:
                pass

        location_by_msg_id: Dict[int, WALocationRef] = {}
        if schema.capabilities.get("has_message_location"):
            try:
                ml_cols = set(schema.columns.get("message_location", ()))
                dur_col = "live_location_share_duration" if "live_location_share_duration" in ml_cols else "0"
                pname_col = "place_name" if "place_name" in ml_cols else "NULL"
                paddr_col = "place_address" if "place_address" in ml_cols else "NULL"
                url_col = "url" if "url" in ml_cols else "NULL"
                cursor.execute(
                    f"""
                    SELECT message_row_id, latitude, longitude, {pname_col}, {paddr_col}, {url_col},
                           {dur_col}
                    FROM message_location
                    """
                )
                for loc_row in cursor.fetchall():
                    l_row_id, lat, lon, pname, paddr, url, live_dur = loc_row
                    location_by_msg_id[l_row_id] = WALocationRef(
                        latitude=lat,
                        longitude=lon,
                        place_name=pname,
                        place_address=paddr,
                        url=url,
                        live_duration=live_dur or 0,
                    )
            except Exception:
                pass

        revocations_list: List[WARevocation] = []
        revoked_msg_ids: Set[int] = set()
        if schema.capabilities.get("has_message_revoked"):
            try:
                mr_cols = set(schema.columns.get("message_revoked", ()))
                admin_col = "admin_jid_row_id" if "admin_jid_row_id" in mr_cols else "NULL"
                cursor.execute(f"SELECT message_row_id, revoked_key_id, {admin_col} FROM message_revoked")
                for r_row in cursor.fetchall():
                    r_row_id, rev_key, admin_jid_id = r_row
                    revoked_msg_ids.add(r_row_id)
                    admin_str = jids_by_id.get(admin_jid_id, {}).get("raw_string") if admin_jid_id else None
                    finding_id = deterministic_finding_id(
                        method="whatsapp_revocation",
                        evidence_sha256=self.evidence_sha256,
                        source_table="message_revoked",
                        row_or_offset=r_row_id,
                        key_facts={"revoked_key_id": rev_key},
                    )
                    revocations_list.append(
                        WARevocation(
                            finding_id=finding_id,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=(
                                "does not prove whether recipient read original message before revocation",
                                "original message body is not preserved in live database row",
                            ),
                            provenance=Provenance(
                                evidence_id=self.evidence_id,
                                evidence_sha256=self.evidence_sha256,
                                source_table="message_revoked",
                                row_id=r_row_id,
                                method="sqlite_message_revoked",
                                derived_from_artifact_id=self.derived_from_artifact_id,
                            ),
                            message_row_id=r_row_id,
                            revoked_key_id=rev_key,
                            admin_jid=admin_str,
                        )
                    )
            except Exception:
                pass

        edits_list: List[WAEdit] = []
        edited_msg_ids: Set[int] = set()
        if schema.capabilities.get("has_message_edit_info"):
            try:
                cursor.execute(
                    "SELECT message_row_id, original_key_id, edit_type, original_timestamp FROM message_edit_info"
                )
                for e_row in cursor.fetchall():
                    e_row_id, orig_key, edit_type, orig_ts = e_row
                    edited_msg_ids.add(e_row_id)
                    finding_id = deterministic_finding_id(
                        method="whatsapp_edit",
                        evidence_sha256=self.evidence_sha256,
                        source_table="message_edit_info",
                        row_or_offset=e_row_id,
                        key_facts={"original_key_id": orig_key, "original_timestamp": orig_ts or 0},
                    )
                    edits_list.append(
                        WAEdit(
                            finding_id=finding_id,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=(
                                "prior text is not present in live database row",
                                "intermediate edit versions require WAL or carved cell recovery",
                            ),
                            provenance=Provenance(
                                evidence_id=self.evidence_id,
                                evidence_sha256=self.evidence_sha256,
                                source_table="message_edit_info",
                                row_id=e_row_id,
                                method="sqlite_message_edit_info",
                                derived_from_artifact_id=self.derived_from_artifact_id,
                            ),
                            message_row_id=e_row_id,
                            original_key_id=orig_key,
                            edited_ts=orig_ts or 0,
                            prior_text_not_present=True,
                        )
                    )
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 6. Parse Message Table (Deterministic Row-ID Order)
        # ---------------------------------------------------------------------
        cursor.execute(
            """
            SELECT _id, chat_row_id, from_me, key_id, sender_jid_row_id, status,
                   timestamp, received_timestamp, message_type, text_data,
                   starred, origination_flags
            FROM message
            ORDER BY _id ASC
            """
        )
        msg_rows = cursor.fetchall()
        messages_list: List[WAMessage] = []

        for m_row in msg_rows:
            (
                row_id,
                chat_row_id,
                from_me,
                key_id,
                sender_jid_row_id,
                status,
                ts,
                rcv_ts,
                msg_type_code,
                text_data,
                starred,
                orig_flags,
            ) = m_row

            chat_meta = chats_by_id.get(chat_row_id, {})
            chat_jid_str = chat_meta.get("chat_jid", str(chat_row_id))
            is_grp = chat_meta.get("is_group", False)

            # Determine sender JID
            if sender_jid_row_id and sender_jid_row_id in jids_by_id:
                sender_jid_str = jids_by_id[sender_jid_row_id]["raw_string"]
            elif from_me == 1:
                sender_jid_str = primary_user_jid or "me"
            else:
                sender_jid_str = chat_jid_str

            # Flags
            flags: List[str] = []
            if orig_flags and (orig_flags & 1):
                flags.append("forwarded")
            if row_id in quoted_by_msg_id:
                flags.append("quoted_reply")
            if row_id in revoked_msg_ids or msg_type_code == 12:
                flags.append("revoked")
            if row_id in edited_msg_ids:
                flags.append("edited")

            # Determine message type name
            if row_id in revoked_msg_ids or msg_type_code == 12:
                type_name = "revoked"
                final_text = None  # Revoked body is nullified per WhatsApp protocol
            else:
                type_name = WA_MESSAGE_TYPE_MAP.get(msg_type_code, f"unknown:{msg_type_code}")
                final_text = text_data

            msg_obj = WAMessage(
                row_id=row_id,
                key_id=key_id,
                chat_row_id=chat_row_id,
                chat_jid=chat_jid_str,
                from_me=from_me,
                sender_jid=sender_jid_str,
                message_type_code=msg_type_code,
                message_type_name=type_name,
                text=final_text,
                ts_raw=ts,
                ts_unit="ms",
                ts_utc_ms=ts,
                received_ts_raw=rcv_ts,
                status=status or 0,
                starred=bool(starred),
                media_ref=media_by_msg_id.get(row_id),
                quoted_ref=quoted_by_msg_id.get(row_id),
                location_ref=location_by_msg_id.get(row_id),
                flags=tuple(flags),
                provenance=Provenance(
                    evidence_id=self.evidence_id,
                    evidence_sha256=self.evidence_sha256,
                    source_table="message",
                    row_id=row_id,
                    method="sqlite_message",
                    derived_from_artifact_id=self.derived_from_artifact_id,
                ),
            )
            messages_list.append(msg_obj)
        # Fallback for transitional schemas where `message` is empty but `messages` table holds data
        if len(messages_list) == 0 and "messages" in schema.tables:
            msg_cols = set(schema.columns.get("messages", ()))
            col_id = "_id" if "_id" in msg_cols else "rowid"
            col_key = "key_id" if "key_id" in msg_cols else "NULL"
            col_remote = "key_remote_jid" if "key_remote_jid" in msg_cols else "remote_jid"
            col_from_me = "key_from_me" if "key_from_me" in msg_cols else "from_me"
            col_data = "data" if "data" in msg_cols else ("text_data" if "text_data" in msg_cols else "NULL")
            col_ts = "timestamp" if "timestamp" in msg_cols else "0"
            col_type = "media_wa_type" if "media_wa_type" in msg_cols else ("message_type" if "message_type" in msg_cols else "0")
            col_status = "status" if "status" in msg_cols else "0"
            col_resource = "remote_resource" if "remote_resource" in msg_cols else "NULL"
            col_starred = "starred" if "starred" in msg_cols else "0"

            query = f"""
                SELECT {col_id}, {col_key}, {col_remote}, {col_from_me}, {col_data},
                       {col_ts}, {col_type}, {col_status}, {col_resource}, {col_starred}
                FROM messages
                ORDER BY {col_id} ASC
            """
            cursor.execute(query)
            for row in cursor.fetchall():
                r_id, k_id, remote_jid, from_me, data, ts, wa_type, status, remote_res, starred = row
                remote_jid = str(remote_jid or "")
                def _s_int(v, d=0):
                    try:
                        return int(v)
                    except (ValueError, TypeError):
                        return d
                parsed_r_id = _s_int(r_id, 0)
                from_me = _s_int(from_me, 0)
                wa_type = _s_int(wa_type, 0)
                parsed_ts = _s_int(ts, 0)
                parsed_status = _s_int(status, 0)

                sender = "me" if from_me == 1 else (str(remote_res) if remote_res else remote_jid)
                type_name = WA_MESSAGE_TYPE_MAP.get(wa_type, f"unknown:{wa_type}")

                msg_obj = WAMessage(
                    row_id=parsed_r_id,
                    key_id=str(k_id or f"transitional_{parsed_r_id}"),
                    chat_row_id=None,
                    chat_jid=remote_jid,
                    from_me=from_me,
                    sender_jid=sender,
                    message_type_code=wa_type,
                    message_type_name=type_name,
                    text=data,
                    ts_raw=parsed_ts,
                    ts_unit="ms",
                    ts_utc_ms=parsed_ts,
                    received_ts_raw=None,
                    status=parsed_status,
                    starred=bool(starred),
                    media_ref=None,
                    quoted_ref=None,
                    location_ref=None,
                    flags=(),
                    provenance=Provenance(
                        evidence_id=self.evidence_id,
                        evidence_sha256=self.evidence_sha256,
                        source_table="messages",
                        row_id=parsed_r_id,
                        method="sqlite_transitional_messages",
                        derived_from_artifact_id=self.derived_from_artifact_id,
                    ),
                )
                messages_list.append(msg_obj)

        cursor.close()

        return WAParseResult(
            schema_family=schema,
            messages=tuple(messages_list),
            chats=tuple(chats_list),
            contacts=tuple(contacts_list),
            group_participants=tuple(group_participants),
            revocations=tuple(revocations_list),
            edits=tuple(edits_list),
            limitations=tuple(limitations),
        )

    def _parse_legacy(self, conn: sqlite3.Connection, schema: SchemaFamily) -> WAParseResult:
        cursor = conn.cursor()
        limitations: List[str] = ["Legacy WhatsApp database format parsed (messages table structure)."]

        msg_table = "messages" if "messages" in schema.tables else "message"
        quoted_table = quote_ident(msg_table)

        # Inspect available columns
        cols = set(schema.columns.get(msg_table, ()))
        col_id = "_id" if "_id" in cols else "rowid"
        col_key = "key_id" if "key_id" in cols else col_id
        col_remote = "key_remote_jid" if "key_remote_jid" in cols else "''"
        col_from_me = "key_from_me" if "key_from_me" in cols else "0"
        col_data = "data" if "data" in cols else ("text_data" if "text_data" in cols else "NULL")
        col_ts = "timestamp" if "timestamp" in cols else "0"
        col_type = "media_wa_type" if "media_wa_type" in cols else "0"
        col_status = "status" if "status" in cols else "0"
        col_resource = "remote_resource" if "remote_resource" in cols else "NULL"
        col_starred = "starred" if "starred" in cols else "0"

        query = f"""
            SELECT {col_id}, {col_key}, {col_remote}, {col_from_me}, {col_data},
                   {col_ts}, {col_type}, {col_status}, {col_resource}, {col_starred}
            FROM {quoted_table}
            ORDER BY {col_id} ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        messages_list: List[WAMessage] = []
        chats_dict: Dict[str, WAChat] = {}
        contacts_dict: Dict[str, WAContact] = {}

        def _safe_int(val, default=0):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        for row in rows:
            r_id, k_id, remote_jid, from_me, data, ts, wa_type, status, remote_res, starred = row
            remote_jid = str(remote_jid or "")
            from_me = _safe_int(from_me, 0)
            wa_type = _safe_int(wa_type, 0)
            parsed_r_id = _safe_int(r_id, 0)
            parsed_ts = _safe_int(ts, 0)
            parsed_status = _safe_int(status, 0)
            
            # Sender JID determination
            if from_me == 1:
                sender = "me"
            elif remote_res:
                sender = str(remote_res)
            else:
                sender = remote_jid

            type_name = WA_MESSAGE_TYPE_MAP.get(wa_type, f"unknown:{wa_type}")
            is_grp = remote_jid.endswith("@g.us")

            if remote_jid and remote_jid not in chats_dict:
                chats_dict[remote_jid] = WAChat(
                    chat_row_id=len(chats_dict) + 1,
                    chat_jid=remote_jid,
                    subject=None,
                    is_group=is_grp,
                    hidden=0,
                    archived=0,
                    last_message_row_id=parsed_r_id,
                    participant_jids=(remote_jid,),
                    provenance=Provenance(
                        evidence_id=self.evidence_id,
                        evidence_sha256=self.evidence_sha256,
                        source_table=msg_table,
                        row_id=parsed_r_id,
                        method="sqlite_legacy_chat",
                        derived_from_artifact_id=self.derived_from_artifact_id,
                    ),
                )
                contacts_dict[remote_jid] = WAContact(
                    jid=remote_jid,
                    display_name=remote_jid,
                    phone_number=remote_jid.split("@")[0] if "@s.whatsapp.net" in remote_jid else None,
                    is_group=is_grp,
                    source="legacy_messages",
                    provenance=Provenance(
                        evidence_id=self.evidence_id,
                        evidence_sha256=self.evidence_sha256,
                        source_table=msg_table,
                        row_id=parsed_r_id,
                        method="sqlite_legacy_contact",
                        derived_from_artifact_id=self.derived_from_artifact_id,
                    ),
                )

            msg_obj = WAMessage(
                row_id=parsed_r_id,
                key_id=str(k_id or f"legacy_{parsed_r_id}"),
                chat_row_id=chats_dict[remote_jid].chat_row_id if remote_jid in chats_dict else None,
                chat_jid=remote_jid,
                from_me=from_me,
                sender_jid=sender,
                message_type_code=wa_type,
                message_type_name=type_name,
                text=data,
                ts_raw=parsed_ts,
                ts_unit="ms",
                ts_utc_ms=parsed_ts,
                received_ts_raw=None,
                status=parsed_status,
                starred=bool(starred),
                media_ref=None,
                quoted_ref=None,
                location_ref=None,
                flags=(),
                provenance=Provenance(
                    evidence_id=self.evidence_id,
                    evidence_sha256=self.evidence_sha256,
                    source_table=msg_table,
                    row_id=parsed_r_id,
                    method="sqlite_legacy_message",
                    derived_from_artifact_id=self.derived_from_artifact_id,
                ),
            )
            messages_list.append(msg_obj)

        cursor.close()

        return WAParseResult(
            schema_family=schema,
            messages=tuple(messages_list),
            chats=tuple(chats_dict.values()),
            contacts=tuple(contacts_dict.values()),
            group_participants=(),
            revocations=(),
            edits=(),
            limitations=tuple(limitations),
        )
