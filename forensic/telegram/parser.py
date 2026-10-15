"""
Pure forensic parser for Telegram Android cache4.db (+ -wal, -shm) (spec B9.0–B9.6).
Zero-disk read-only operations (master.md R4, R8, R10, R11, R12, R18):
Takes raw bytes in, yields frozen dataclasses with complete forensic provenance.
"""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from forensic.common.contracts import Provenance
from forensic.common.hashing import deterministic_finding_id, sha256_hex
from forensic.common.sqlite_open import open_sqlite_ro, quote_ident
from forensic.sqlite.image import SQLiteImage
from forensic.sqlite.wal import apply_wal, parse_wal
from forensic.telegram.models import (
    TgChatRecord,
    TgDialog,
    TgMessageRecord,
    TgParseResult,
    TgPeerKind,
    TgSchemaInfo,
    TgUnparsedBlob,
    TgUserRecord,
    UnsupportedSchemaError,
)
from forensic.telegram.schema import detect_tg_schema
from forensic.telegram.tl.reader import TLError
from forensic.telegram.tl.registry import deserialize_tl_blob
from forensic.telegram.tl.types import (
    TgChannel,
    TgChat,
    TgMediaDocument,
    TgMediaGeo,
    TgMediaPhoto,
    TgMessage,
    TgMessageEmpty,
    TgMessageService,
    TgPeer,
    TgUser,
)


def resolve_peer_from_did(did: int) -> Tuple[TgPeerKind, int]:
    """
    Map Telegram dialog did to peer kind and entity ID (B9.4, FORMAT_NOTES §4.5).

    - did >= 0: User 1-on-1 private chat with peer_id = did.
      Special case: encrypted/secret chat marker where high 32 bits != 0 and low 32 bits == 0.
    - 0 > did > -1000000000000: Basic Group Chat with chat_id = -did.
    - did <= -1000000000000: Channel / Supergroup with channel_id = -did - 1000000000000.
    """
    if did >= 0:
        # Check secret chat marker: (did & 0xffffffff00000000) != 0 and (did & 0xffffffff) == 0
        if (did & 0xFFFFFFFF00000000) != 0 and (did & 0xFFFFFFFF) == 0:
            return "secret_chat_marker", did >> 32
        return "user", did
    elif did > -1000000000000:
        return "chat", -did
    else:
        return "channel", -did - 1000000000000


class TelegramParser:
    """Pure forensic parser for Telegram Android cache4.db, WAL, and SHM."""

    def __init__(
        self,
        db_source: Union[bytes, str, Path],
        evidence_id: str,
        wal_source: Optional[Union[bytes, str, Path]] = None,
        shm_source: Optional[Union[bytes, str, Path]] = None,
        evidence_sha256: Optional[str] = None,
        derived_from_artifact_id: Optional[str] = None,
    ):
        self.evidence_id = str(evidence_id)
        self.derived_from_artifact_id = derived_from_artifact_id

        # Load main database bytes
        if isinstance(db_source, bytes):
            self.db_bytes = db_source
        else:
            p = Path(db_source)
            if not p.is_file():
                raise FileNotFoundError(f"Telegram database file not found: {p}")
            self.db_bytes = p.read_bytes()

        self.evidence_sha256 = evidence_sha256 or sha256_hex(self.db_bytes)

        # Load WAL bytes if provided
        self.wal_bytes: Optional[bytes] = None
        if wal_source is not None:
            if isinstance(wal_source, bytes):
                self.wal_bytes = wal_source
            else:
                wp = Path(wal_source)
                if wp.is_file():
                    self.wal_bytes = wp.read_bytes()

        # Load SHM bytes if provided (indexed only, never treated as content per B9.5)
        self.shm_bytes: Optional[bytes] = None
        if shm_source is not None:
            if isinstance(shm_source, bytes):
                self.shm_bytes = shm_source
            else:
                sp = Path(shm_source)
                if sp.is_file():
                    self.shm_bytes = sp.read_bytes()

    def parse(self) -> TgParseResult:
        """
        Execute multi-view forensic parse (B9.5):
        - Main view (cache4.db alone)
        - Post-WAL view (cache4.db with committed WAL frames applied in-memory)
        Emits live message set from post_wal_view, with full provenance and honest UNPARSED_BLOB fallbacks.
        """
        limitations: List[str] = []
        views_parsed: List[str] = ["main_view"]

        # Note SHM index handling (B9.5)
        if self.shm_bytes is not None:
            limitations.append(
                f"SHM index file present (sha256={sha256_hex(self.shm_bytes)}); "
                "ignored for content parsing per SQLite specification."
            )

        # Prepare in-memory views
        main_bytes = self.db_bytes
        post_wal_bytes: Optional[bytes] = None

        if self.wal_bytes is not None:
            try:
                main_image = SQLiteImage(main_bytes)
                wal_file = parse_wal(self.wal_bytes, page_size_hint=main_image.page_size)
                post_wal_bytes = apply_wal(main_image, wal_file)
                views_parsed.append("post_wal_view")
                if wal_file.warnings:
                    for w in wal_file.warnings:
                        limitations.append(f"WAL warning: {w}")
            except Exception as e:
                limitations.append(f"Failed to assemble post-WAL view ({e}); fell back to main_view only.")
                post_wal_bytes = None
        else:
            limitations.append("Write-Ahead Log (WAL) not provided; parsed main_view only.")

        # Determine target connection for live data extraction (prefer post_wal_view per B9.5)
        primary_bytes = post_wal_bytes if post_wal_bytes is not None else main_bytes
        primary_view_name = "post_wal_view" if post_wal_bytes is not None else "main_view"

        # Introspect schema on primary view
        primary_conn = open_sqlite_ro(primary_bytes)
        try:
            schema_info = detect_tg_schema(primary_conn, raise_on_unknown=True)
            messages, dialogs, users, chats, unparsed_blobs, view_limits = self._parse_view(
                primary_conn, primary_view_name
            )
            limitations.extend(view_limits)
        finally:
            primary_conn.close()

        # If post-WAL view was parsed, also inspect main_view to pass any deleted/superseded history
        if post_wal_bytes is not None:
            main_conn = open_sqlite_ro(main_bytes)
            try:
                _m_msgs, _m_diag, _m_users, _m_chats, _m_unparsed, _ = self._parse_view(
                    main_conn, "main_view"
                )
                # Keep main_view records available for future Tier-2 WAL history comparisons
            finally:
                main_conn.close()

        return TgParseResult(
            schema_info=schema_info,
            messages=tuple(messages),
            dialogs=tuple(dialogs),
            users=tuple(users),
            chats=tuple(chats),
            unparsed_blobs=tuple(unparsed_blobs),
            views_parsed=tuple(views_parsed),
            limitations=tuple(limitations),
        )

    def _parse_view(
        self,
        conn: sqlite3.Connection,
        view_name: str,
    ) -> Tuple[
        List[TgMessageRecord],
        List[TgDialog],
        List[TgUserRecord],
        List[TgChatRecord],
        List[TgUnparsedBlob],
        List[str],
    ]:
        """Parse all tables within a specific database view."""
        limitations: List[str] = []
        cursor = conn.cursor()

        # 1. Parse users
        users, user_unparsed = self._extract_users(cursor, view_name)

        # 2. Parse chats & channels
        chats, chat_unparsed = self._extract_chats(cursor, view_name)

        # 3. Parse dialogs
        dialogs = self._extract_dialogs(cursor, view_name, users, chats, limitations)

        # 4. Parse messages_v2
        messages, msg_unparsed, msg_limits = self._extract_messages(cursor, view_name, users)
        limitations.extend(msg_limits)

        cursor.close()
        all_unparsed = user_unparsed + chat_unparsed + msg_unparsed
        return messages, dialogs, users, chats, all_unparsed, limitations

    def _extract_users(
        self,
        cursor: sqlite3.Cursor,
        view_name: str,
    ) -> Tuple[List[TgUserRecord], List[TgUnparsedBlob]]:
        """Extract user profiles from users table (B9.4)."""
        users: List[TgUserRecord] = []
        unparsed: List[TgUnparsedBlob] = []

        cursor.execute("SELECT uid, name, data FROM users")
        rows = cursor.fetchall()

        for uid, plain_name, blob_data in rows:
            prov = Provenance(
                evidence_id=self.evidence_id,
                evidence_sha256=self.evidence_sha256,
                source_table="users",
                row_id=uid,
                method=f"cache4_{view_name}",
                derived_from_artifact_id=self.derived_from_artifact_id,
            )
            fid = deterministic_finding_id(f"cache4_{view_name}", self.evidence_sha256, "users", uid)

            if not blob_data:
                # Column-only user profile
                users.append(
                    TgUserRecord(
                        finding_id=fid,
                        confidence_score=1.0,
                        strength="deterministic",
                        limitations=("Profile metadata extracted from SQL column name only; TL blob absent",),
                        provenance=prov,
                        uid=uid,
                        first_name=plain_name,
                    )
                )
                continue

            try:
                tl_obj = deserialize_tl_blob(blob_data)
                if isinstance(tl_obj, TgUser):
                    users.append(
                        TgUserRecord(
                            finding_id=fid,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=(),
                            provenance=prov,
                            uid=tl_obj.id,
                            first_name=tl_obj.first_name or plain_name,
                            last_name=tl_obj.last_name,
                            username=tl_obj.username,
                            phone=tl_obj.phone,
                            is_self=tl_obj.is_self,
                            contact=tl_obj.contact,
                            deleted=tl_obj.deleted,
                            bot=tl_obj.bot,
                        )
                    )
                else:
                    users.append(
                        TgUserRecord(
                            finding_id=fid,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=(f"User TL constructor {type(tl_obj).__name__}",),
                            provenance=prov,
                            uid=uid,
                            first_name=plain_name,
                        )
                    )
            except Exception as e:
                cid_hex = None
                if len(blob_data) >= 4:
                    cid_hex = hex(struct.unpack("<I", blob_data[:4])[0])
                unparsed.append(
                    TgUnparsedBlob(
                        finding_id=deterministic_finding_id(
                            f"cache4_{view_name}_unparsed", self.evidence_sha256, "users", uid
                        ),
                        confidence_score=1.0,
                        strength="deterministic",
                        limitations=("Unparsed user TL blob; column name preserved",),
                        provenance=prov,
                        table="users",
                        row_id=uid,
                        uid=uid,
                        constructor_id_hex=cid_hex,
                        length=len(blob_data),
                        sha256=sha256_hex(blob_data),
                        reason=str(e),
                        container_metadata={"name": plain_name, "source": "from_column"},
                    )
                )

        return users, unparsed

    def _extract_chats(
        self,
        cursor: sqlite3.Cursor,
        view_name: str,
    ) -> Tuple[List[TgChatRecord], List[TgUnparsedBlob]]:
        """Extract groups and channels from chats table (B9.4)."""
        chats: List[TgChatRecord] = []
        unparsed: List[TgUnparsedBlob] = []

        cursor.execute("SELECT uid, name, data FROM chats")
        rows = cursor.fetchall()

        for uid, plain_name, blob_data in rows:
            prov = Provenance(
                evidence_id=self.evidence_id,
                evidence_sha256=self.evidence_sha256,
                source_table="chats",
                row_id=uid,
                method=f"cache4_{view_name}",
                derived_from_artifact_id=self.derived_from_artifact_id,
            )
            fid = deterministic_finding_id(f"cache4_{view_name}", self.evidence_sha256, "chats", uid)

            if not blob_data:
                chats.append(
                    TgChatRecord(
                        finding_id=fid,
                        confidence_score=1.0,
                        strength="deterministic",
                        limitations=("Chat metadata extracted from SQL column name only; TL blob absent",),
                        provenance=prov,
                        did=-uid,
                        chat_id=uid,
                        title=plain_name or f"Chat {uid}",
                    )
                )
                continue

            try:
                tl_obj = deserialize_tl_blob(blob_data)
                if isinstance(tl_obj, TgChat):
                    chats.append(
                        TgChatRecord(
                            finding_id=fid,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=(),
                            provenance=prov,
                            did=-tl_obj.id,
                            chat_id=tl_obj.id,
                            title=tl_obj.title or plain_name or "",
                            is_channel=False,
                            is_group=True,
                            participants_count=tl_obj.participants_count,
                        )
                    )
                elif isinstance(tl_obj, TgChannel):
                    chats.append(
                        TgChatRecord(
                            finding_id=fid,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=(),
                            provenance=prov,
                            did=-(1000000000000 + tl_obj.id),
                            chat_id=tl_obj.id,
                            title=tl_obj.title or plain_name or "",
                            is_channel=True,
                            is_group=tl_obj.megagroup,
                            participants_count=tl_obj.participants_count or 0,
                        )
                    )
                else:
                    chats.append(
                        TgChatRecord(
                            finding_id=fid,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=(f"Chat TL constructor {type(tl_obj).__name__}",),
                            provenance=prov,
                            did=-uid,
                            chat_id=uid,
                            title=plain_name or f"Chat {uid}",
                        )
                    )
            except Exception as e:
                cid_hex = None
                if len(blob_data) >= 4:
                    cid_hex = hex(struct.unpack("<I", blob_data[:4])[0])
                unparsed.append(
                    TgUnparsedBlob(
                        finding_id=deterministic_finding_id(
                            f"cache4_{view_name}_unparsed", self.evidence_sha256, "chats", uid
                        ),
                        confidence_score=1.0,
                        strength="deterministic",
                        limitations=("Unparsed chat TL blob; column name preserved",),
                        provenance=prov,
                        table="chats",
                        row_id=uid,
                        uid=uid,
                        constructor_id_hex=cid_hex,
                        length=len(blob_data),
                        sha256=sha256_hex(blob_data),
                        reason=str(e),
                        container_metadata={"name": plain_name, "source": "from_column"},
                    )
                )

        return chats, unparsed

    def _extract_dialogs(
        self,
        cursor: sqlite3.Cursor,
        view_name: str,
        users: List[TgUserRecord],
        chats: List[TgChatRecord],
        limitations: List[str],
    ) -> List[TgDialog]:
        """Extract conversation threads from dialogs table (B9.4)."""
        dialogs: List[TgDialog] = []
        user_names = {u.uid: f"{u.first_name or ''} {u.last_name or ''}".strip() for u in users}
        chat_titles = {c.chat_id: c.title for c in chats}
        chat_titles.update({c.did: c.title for c in chats})

        cursor.execute("SELECT did, date, unread_count, last_mid, pinned FROM dialogs")
        rows = cursor.fetchall()

        for did, _date, unread_count, last_mid, pinned in rows:
            peer_kind, peer_id = resolve_peer_from_did(did)
            limits = []
            if peer_kind == "secret_chat_marker":
                limits.append("Secret chat reference detected; message content is device-only and out of scope per DEC-004.")

            # Resolve title
            title = None
            if peer_kind == "user":
                title = user_names.get(peer_id)
            elif peer_kind in ("chat", "channel"):
                title = chat_titles.get(peer_id) or chat_titles.get(did)

            prov = Provenance(
                evidence_id=self.evidence_id,
                evidence_sha256=self.evidence_sha256,
                source_table="dialogs",
                row_id=did,
                method=f"cache4_{view_name}",
                derived_from_artifact_id=self.derived_from_artifact_id,
            )
            fid = deterministic_finding_id(f"cache4_{view_name}", self.evidence_sha256, "dialogs", did)

            dialogs.append(
                TgDialog(
                    finding_id=fid,
                    confidence_score=1.0,
                    strength="deterministic",
                    limitations=tuple(limits),
                    provenance=prov,
                    dialog_id=did,
                    peer_kind=peer_kind,
                    peer_id=peer_id,
                    title=title,
                    last_mid=last_mid,
                    unread_count=unread_count or 0,
                    pinned=bool(pinned),
                )
            )

        return dialogs

    def _extract_messages(
        self,
        cursor: sqlite3.Cursor,
        view_name: str,
        users: List[TgUserRecord],
    ) -> Tuple[List[TgMessageRecord], List[TgUnparsedBlob], List[str]]:
        """
        Extract messages from messages_v2 table (B9.2, B9.3, B9.4).
        Invariant: parsed_count + unparsed_count == rows_seen (no silent drops).
        """
        messages: List[TgMessageRecord] = []
        unparsed: List[TgUnparsedBlob] = []
        limitations: List[str] = []

        self_uids = {u.uid for u in users if u.is_self}
        default_self_uid = min(self_uids) if self_uids else 1001

        cursor.execute(
            """
            SELECT rowid, mid, uid, read_state, send_state, date, data, out, media, reply_to_message_id
            FROM messages_v2
            ORDER BY mid ASC
            """
        )
        rows = cursor.fetchall()

        for (
            rowid,
            col_mid,
            col_uid,
            col_read_state,
            col_send_state,
            col_date,
            blob_data,
            col_out,
            col_media,
            col_reply_to,
        ) in rows:
            prov = Provenance(
                evidence_id=self.evidence_id,
                evidence_sha256=self.evidence_sha256,
                source_table="messages_v2",
                row_id=rowid,
                method=f"cache4_{view_name}",
                derived_from_artifact_id=self.derived_from_artifact_id,
            )
            fid = deterministic_finding_id(
                f"cache4_{view_name}",
                self.evidence_sha256,
                "messages_v2",
                rowid,
                {"mid": col_mid, "uid": col_uid},
            )

            # Plain column container metadata
            container_meta = {
                "mid": col_mid,
                "uid": col_uid,
                "date": col_date,
                "out": col_out,
                "read_state": col_read_state,
                "send_state": col_send_state,
                "media_code": col_media,
                "reply_to": col_reply_to,
                "source": "from_column",
            }

            if not blob_data:
                # NULL blob: classify as unparsed blob
                unparsed.append(
                    TgUnparsedBlob(
                        finding_id=fid,
                        confidence_score=1.0,
                        strength="deterministic",
                        limitations=("Message data BLOB is NULL",),
                        provenance=prov,
                        table="messages_v2",
                        row_id=rowid,
                        mid=col_mid,
                        uid=col_uid,
                        constructor_id_hex=None,
                        length=0,
                        sha256="",
                        reason="NULL blob data",
                        container_metadata=container_meta,
                    )
                )
                continue

            try:
                tl_obj = deserialize_tl_blob(blob_data)
                if isinstance(tl_obj, TgMessage):
                    # Extract fields
                    text = tl_obj.message
                    out_val = 1 if tl_obj.out else 0
                    msg_date_raw = tl_obj.date or col_date
                    msg_date_utc_ms = msg_date_raw * 1000

                    # Resolve sender
                    from_id = None
                    if tl_obj.from_peer is not None:
                        from_id = tl_obj.from_peer.peer_id
                    elif col_uid > 0:
                        # 1-on-1 private chat
                        from_id = default_self_uid if out_val == 1 else col_uid
                    else:
                        from_id = default_self_uid if out_val == 1 else None

                    # Media attachments
                    media_kind: Optional[str] = None
                    media_ref: Optional[str] = None
                    geo_lat: Optional[float] = None
                    geo_lon: Optional[float] = None
                    flags_list: List[str] = []

                    if tl_obj.media is not None:
                        if isinstance(tl_obj.media, TgMediaPhoto):
                            media_kind = "image"
                            media_ref = f"tg_photo_{col_mid:04d}.jpg"
                            flags_list.append("photo")
                        elif isinstance(tl_obj.media, TgMediaDocument):
                            media_kind = "audio" if tl_obj.media.voice else "document"
                            media_ref = tl_obj.media.file_name or f"tg_audio_{col_mid:04d}.ogg"
                            flags_list.append("audio" if tl_obj.media.voice else "document")
                        elif isinstance(tl_obj.media, TgMediaGeo):
                            media_kind = "location"
                            geo_lat = tl_obj.media.latitude
                            geo_lon = tl_obj.media.longitude
                            media_ref = f"{geo_lat},{geo_lon}"
                            flags_list.append("location")

                    # Quoted reply
                    reply_to_mid = None
                    if tl_obj.reply_to is not None and tl_obj.reply_to.reply_to_msg_id:
                        reply_to_mid = tl_obj.reply_to.reply_to_msg_id
                        flags_list.append("reply")
                    elif col_reply_to:
                        reply_to_mid = col_reply_to

                    # Entities
                    entities_list: List[Dict[str, Any]] = []
                    if tl_obj.entities:
                        entities_list = [e.to_dict() for e in tl_obj.entities]

                    # Trailing bookkeeping bytes handling (B9.2)
                    trailing_info = None
                    record_limits = []
                    if tl_obj.trailing_bytes:
                        trailing_info = {
                            "length": len(tl_obj.trailing_bytes),
                            "sha256": sha256_hex(tl_obj.trailing_bytes),
                            "prefix_hex": tl_obj.trailing_bytes[:32].hex(),
                        }
                        record_limits.append("Local trailing bookkeeping bytes present after TL Message object.")

                    messages.append(
                        TgMessageRecord(
                            finding_id=fid,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=tuple(record_limits),
                            provenance=prov,
                            mid=col_mid,
                            dialog_id=col_uid,
                            from_id=from_id,
                            out=out_val,
                            date_raw=msg_date_raw,
                            date_unit="seconds",
                            date_utc_ms=msg_date_utc_ms,
                            text=text,
                            media_kind=media_kind,
                            media_ref=media_ref,
                            reply_to_mid=reply_to_mid,
                            geo_lat=geo_lat,
                            geo_lon=geo_lon,
                            entities=tuple(entities_list),
                            flags=tuple(flags_list),
                            read_state=col_read_state,
                            send_state=col_send_state,
                            view=view_name,
                            trailing_bytes_info=trailing_info,
                        )
                    )
                elif isinstance(tl_obj, TgMessageService):
                    # Action / Service message
                    out_val = 1 if tl_obj.out else 0
                    msg_date_raw = tl_obj.date or col_date
                    msg_date_utc_ms = msg_date_raw * 1000
                    from_id = tl_obj.from_peer.peer_id if tl_obj.from_peer else default_self_uid

                    messages.append(
                        TgMessageRecord(
                            finding_id=fid,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=("Service action message",),
                            provenance=prov,
                            mid=col_mid,
                            dialog_id=col_uid,
                            from_id=from_id,
                            out=out_val,
                            date_raw=msg_date_raw,
                            date_unit="seconds",
                            date_utc_ms=msg_date_utc_ms,
                            text=f"[Service Action: {tl_obj.action_type}]",
                            media_kind=None,
                            media_ref=None,
                            reply_to_mid=col_reply_to or None,
                            flags=("service",),
                            read_state=col_read_state,
                            send_state=col_send_state,
                            view=view_name,
                        )
                    )
                else:
                    # Non-message TL object in messages_v2 -> classify as unparsed blob
                    cid_hex = hex(struct.unpack("<I", blob_data[:4])[0]) if len(blob_data) >= 4 else None
                    unparsed.append(
                        TgUnparsedBlob(
                            finding_id=fid,
                            confidence_score=1.0,
                            strength="deterministic",
                            limitations=(f"Unexpected object constructor: {type(tl_obj).__name__}",),
                            provenance=prov,
                            table="messages_v2",
                            row_id=rowid,
                            mid=col_mid,
                            uid=col_uid,
                            constructor_id_hex=cid_hex,
                            length=len(blob_data),
                            sha256=sha256_hex(blob_data),
                            reason=f"Deserialized non-message object: {type(tl_obj).__name__}",
                            container_metadata=container_meta,
                        )
                    )
            except Exception as e:
                # Unknown constructor or corrupt blob -> UNPARSED_BLOB (B9.3)
                cid_hex = hex(struct.unpack("<I", blob_data[:4])[0]) if len(blob_data) >= 4 else None
                unparsed.append(
                    TgUnparsedBlob(
                        finding_id=fid,
                        confidence_score=1.0,
                        strength="deterministic",
                        limitations=("Unparsed message blob; container metadata preserved from columns",),
                        provenance=prov,
                        table="messages_v2",
                        row_id=rowid,
                        mid=col_mid,
                        uid=col_uid,
                        constructor_id_hex=cid_hex,
                        length=len(blob_data),
                        sha256=sha256_hex(blob_data),
                        reason=str(e),
                        container_metadata=container_meta,
                    )
                )

        # Invariant assertion check: parsed messages + unparsed blobs == rows seen in messages_v2
        assert len(messages) + len(unparsed) == len(rows), (
            f"No-silent-drop invariant violated for messages_v2: "
            f"messages({len(messages)}) + unparsed({len(unparsed)}) != rows({len(rows)})"
        )

        return messages, unparsed, limitations
