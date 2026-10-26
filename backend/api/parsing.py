"""
Forensic Parsing & Universal File Inspector API.
Provides endpoints for:
1. Listing all accessible files from evidence exhibits and decrypted derived artifacts.
2. Inspecting underlying SQLite database tables with rows/columns, sorting, pagination, and multi-column search.
3. Rendering formatted raw previews for non-database files (XML, JSON, TXT, Logs, Configs).
4. Providing media previews and hex dump representations.
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import tempfile
import traceback
from typing import Any, Dict, List, Optional
import xml.dom.minidom

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Case, DerivedArtifact, Evidence, EvidenceFile

router = APIRouter(tags=["parsing"])


def _try_parse_tl_or_binary_blob(val: bytes, col_name: str = "") -> Any:
    """Intelligently inspect and parse binary blobs (e.g. Telegram MTProto TL serialized blobs)."""
    # 1. Try plain utf-8 decode
    try:
        decoded = val.decode("utf-8")
        if all(ord(c) >= 32 or c in "\r\n\t" for c in decoded):
            return decoded
    except Exception:
        pass

    # 2. Try Telegram MTProto TL deserialization for data / TL blobs
    try:
        from forensic.telegram.tl.registry import deserialize_tl_blob
        from forensic.telegram.tl.types import TgMessage, TgUser, TgChat, TgChannel

        tl_obj = deserialize_tl_blob(val)
        if isinstance(tl_obj, TgMessage):
            parsed_text = tl_obj.message or ""
            return parsed_text if parsed_text else f"[Message recorded on {tl_obj.date}]"
        elif isinstance(tl_obj, TgUser):
            name_parts = [p for p in (tl_obj.first_name, tl_obj.last_name) if p]
            name = " ".join(name_parts)
            handle = f" (@{tl_obj.username})" if tl_obj.username else ""
            phone = f" {tl_obj.phone}" if tl_obj.phone else ""
            user_str = f"{name}{handle}{phone}".strip()
            return user_str if user_str else "Unknown User"
        elif isinstance(tl_obj, (TgChat, TgChannel)):
            title = getattr(tl_obj, "title", "")
            return title if title else f"Chat ({getattr(tl_obj, 'id', '')})"
        else:
            return f"<{len(val)} bytes binary data>"
    except Exception:
        pass

    # 3. Fallback: formatted BLOB identifier
    return f"<{len(val)} bytes binary data>"


def _clean_text_preview(val: Any, col_name: str = "") -> Any:
    """Format cell value for display, handling raw bytes or complex types."""
    if isinstance(val, bytes):
        return _try_parse_tl_or_binary_blob(val, col_name)
    elif isinstance(val, (dict, list)):
        try:
            return json.dumps(val, ensure_ascii=False)
        except Exception:
            return str(val)
    return val


def _generate_hex_dump(buffer: bytes, max_bytes: int = 8192) -> str:
    """Generate canonical hex dump (offset | 16 hex bytes | ascii) for binary files."""
    chunk = buffer[:max_bytes]
    lines = []
    for i in range(0, len(chunk), 16):
        sub = chunk[i : i + 16]
        hex_bytes = " ".join(f"{b:02x}" for b in sub)
        # Pad hex display to 48 chars
        hex_col = hex_bytes.ljust(48)
        ascii_col = "".join(chr(b) if 32 <= b <= 126 else "." for b in sub)
        lines.append(f"{i:08x}  {hex_col}  |{ascii_col}|")
    if len(buffer) > max_bytes:
        lines.append(f"... [Truncated {len(buffer) - max_bytes} bytes for preview]")
    return "\n".join(lines)


def _detect_file_type(filename: str, mime: Optional[str] = None, buffer: Optional[bytes] = None) -> tuple[str, str]:
    """Return (category, specific_type)."""
    fn = filename.lower()
    m = (mime or "").lower()

    if buffer:
        if buffer.startswith(b"SQLite format 3\x00"):
            return "database", "sqlite"
        if buffer.startswith(b"\xff\xd8\xff") or buffer.startswith(b"\x89PNG") or buffer.startswith(b"GIF8") or (b"WEBP" in buffer[:16]):
            return "media", "image"
        if buffer.startswith(b"OggS") or buffer.startswith(b"ID3") or buffer.startswith(b"\xff\xfb"):
            return "media", "audio"

    if fn.endswith((".db", ".sqlite", ".sqlite3")) or "sqlite" in m:
        return "database", "sqlite"
    if fn.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")) or "image/" in m:
        return "media", "image"
    if fn.endswith((".mp4", ".m4v", ".mov")) or "video/" in m:
        return "media", "video"
    if fn.endswith((".opus", ".mp3", ".ogg", ".wav", ".m4a", ".aac")) or "audio/" in m:
        return "media", "audio"
    if fn.endswith(".xml") or "xml" in m:
        return "document", "xml"
    if fn.endswith(".json") or "json" in m:
        return "document", "json"
    if fn.endswith((".log", ".txt", ".ini", ".cfg", ".conf", ".plist")):
        return "document", "text"
    if fn.endswith((".key", ".pub", ".pem", ".cert", ".der")):
        return "document", "key"
    return "other", "binary"


@router.get("/{case_id}/parsing/files")
def list_accessible_parsing_files(
    case_id: int,
    db: Session = Depends(get_db),
):
    """
    List all accessible files for a case (unencrypted evidence members,
    standalone evidence items, and decrypted derived artifacts).
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    evidence_items = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.id.asc())
        .all()
    )
    derived_artifacts = (
        db.query(DerivedArtifact)
        .filter(DerivedArtifact.case_id == case_id)
        .order_by(DerivedArtifact.id.desc())
        .all()
    )

    files_list = []
    seen_file_sigs = set()

    # 1. Add all decrypted derived exhibits (e.g. msgstore_decrypted.db)
    for da in derived_artifacts:
        sig = (da.sha256, da.original_filename) if da.sha256 else (da.id, da.original_filename)
        if sig in seen_file_sigs:
            continue
        seen_file_sigs.add(sig)

        files_list.append({
            "id": f"art_{da.id}",
            "target_type": "derived_artifact",
            "target_id": da.id,
            "filename": da.original_filename,
            "relative_path": f"derived/{da.original_filename}",
            "size_bytes": da.size_bytes or (len(da.content_bytes) if da.content_bytes else 0),
            "sha256": da.sha256,
            "category": "database" if da.artifact_type == "decrypted_sqlite" else "other",
            "file_type": "sqlite" if da.artifact_type == "decrypted_sqlite" else "binary",
            "mime_type": da.mime_type or "application/x-sqlite3",
            "source_container": "Decrypted Derived Exhibit",
            "is_derived": True,
            "parent_evidence_id": da.parent_evidence_id,
        })

    # 2. Add all accessible (unencrypted) evidence members and standalone files
    for ev in evidence_items:
        if ev.files:
            for ef in ev.files:
                fn_lower = ef.relative_path.lower()
                # Skip encrypted containers awaiting decryption
                if any(fn_lower.endswith(ext) for ext in [".crypt", ".crypt12", ".crypt14", ".crypt15"]):
                    continue

                sig = (ef.sha256, ef.relative_path.split("/")[-1]) if ef.sha256 else (ef.id, ef.relative_path)
                if sig in seen_file_sigs:
                    continue
                seen_file_sigs.add(sig)

                cat, spec_type = _detect_file_type(ef.relative_path, ef.mime_type)
                files_list.append({
                    "id": f"file_{ef.id}",
                    "target_type": "evidence_file",
                    "target_id": ef.id,
                    "filename": ef.relative_path.split("/")[-1],
                    "relative_path": ef.relative_path,
                    "size_bytes": ef.file_size or 0,
                    "sha256": ef.sha256,
                    "category": cat,
                    "file_type": spec_type,
                    "mime_type": ef.mime_type or "application/octet-stream",
                    "source_container": ev.original_filename,
                    "is_derived": False,
                    "parent_evidence_id": ev.id,
                })
        else:
            fn_lower = ev.original_filename.lower()
            if any(fn_lower.endswith(ext) for ext in [".crypt", ".crypt12", ".crypt14", ".crypt15"]):
                continue

            sig = (ev.sha256, ev.original_filename) if ev.sha256 else (ev.id, ev.original_filename)
            if sig in seen_file_sigs:
                continue
            seen_file_sigs.add(sig)

            cat, spec_type = _detect_file_type(ev.original_filename, ev.mime_type)
            files_list.append({
                "id": f"ev_{ev.id}",
                "target_type": "evidence",
                "target_id": ev.id,
                "filename": ev.original_filename,
                "relative_path": ev.original_filename,
                "size_bytes": ev.file_size_bytes or 0,
                "sha256": ev.sha256,
                "category": cat,
                "file_type": spec_type,
                "mime_type": ev.mime_type or "application/octet-stream",
                "source_container": ev.original_filename,
                "is_derived": False,
                "parent_evidence_id": ev.id,
            })

    counts = {
        "databases": len([f for f in files_list if f["category"] == "database"]),
        "documents": len([f for f in files_list if f["category"] == "document"]),
        "media": len([f for f in files_list if f["category"] == "media"]),
        "other": len([f for f in files_list if f["category"] not in ("database", "document", "media")]),
    }

    return {
        "case_id": case_id,
        "total_files": len(files_list),
        "counts": counts,
        "files": files_list,
    }


@router.get("/{case_id}/parsing/inspect")
def inspect_case_file(
    case_id: int,
    target_type: str = Query(..., description="derived_artifact | evidence_file | evidence"),
    target_id: int = Query(..., description="ID of the target entity"),
    table_name: Optional[str] = Query(None, description="Active table name for SQLite database"),
    search: Optional[str] = Query(None, description="Search filter across table columns or text"),
    sort_by: Optional[str] = Query(None, description="Column name to sort by"),
    sort_order: Optional[str] = Query("asc", description="Sort direction (asc | desc)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Universally inspect any accessible file in the case:
    - If SQLite database: returns tables list, columns schema, and paginated rows with search & sort.
    - If Text/XML/JSON/Logs: returns full decoded content with line count and formatted representation.
    - If Media: returns preview data URI.
    - If Binary: returns formatted hex dump.
    """
    # Normalize query params when called directly or through FastAPI
    search_str: Optional[str] = search.strip() if isinstance(search, str) and search.strip() else None
    table_name_str: Optional[str] = table_name.strip() if isinstance(table_name, str) and table_name.strip() else None
    sort_by_str: Optional[str] = sort_by.strip() if isinstance(sort_by, str) and sort_by.strip() else None
    sort_order_str: str = sort_order.strip().lower() if isinstance(sort_order, str) and sort_order.strip() else "asc"
    limit_int: int = int(limit) if isinstance(limit, (int, float, str)) and str(limit).isdigit() else 100
    offset_int: int = int(offset) if isinstance(offset, (int, float, str)) and str(offset).isdigit() else 0

    # 1. Resolve raw binary buffer and metadata
    target_bytes: Optional[bytes] = None
    filename: str = ""
    relative_path: str = ""
    size_bytes: int = 0
    sha256_hash: str = ""
    mime_type: Optional[str] = None
    is_derived: bool = False
    source_container: str = ""

    if target_type == "derived_artifact":
        da = db.query(DerivedArtifact).filter(
            DerivedArtifact.id == target_id,
            DerivedArtifact.case_id == case_id,
        ).first()
        if not da or not da.content_bytes:
            raise HTTPException(status_code=404, detail="Derived exhibit not found or content is empty.")
        target_bytes = da.content_bytes
        filename = da.original_filename
        relative_path = f"derived/{da.original_filename}"
        size_bytes = da.size_bytes or len(target_bytes)
        sha256_hash = da.sha256
        mime_type = da.mime_type or "application/x-sqlite3"
        is_derived = True
        source_container = "Decrypted Derived Exhibit"

    elif target_type == "evidence_file":
        ef = db.query(EvidenceFile).filter(EvidenceFile.id == target_id).first()
        if not ef:
            raise HTTPException(status_code=404, detail="Evidence file member not found.")
        target_bytes = ef.content_bytes
        if not target_bytes:
            from backend.utils.file_storage import get_evidence_file_bytes
            target_bytes = get_evidence_file_bytes(ef)
        if not target_bytes and ef.evidence:
            # Fallback to reading from parent evidence archive if zip
            ev_b = ef.evidence.content_bytes
            if ev_b and ev_b.startswith(b"PK\x03\x04"):
                import io, zipfile
                try:
                    with zipfile.ZipFile(io.BytesIO(ev_b)) as z:
                        clean_rel = ef.relative_path.replace("\\", "/")
                        if clean_rel in z.namelist():
                            target_bytes = z.read(clean_rel)
                        else:
                            for name in z.namelist():
                                if name.endswith(clean_rel) or clean_rel.endswith(name):
                                    target_bytes = z.read(name)
                                    break
                except Exception:
                    pass
        filename = ef.relative_path.split("/")[-1]
        relative_path = ef.relative_path
        size_bytes = ef.file_size or (len(target_bytes) if target_bytes else 0)
        sha256_hash = ef.sha256
        mime_type = ef.mime_type
        is_derived = False
        source_container = ef.evidence.original_filename if ef.evidence else "Unknown"

    elif target_type == "evidence":
        ev = db.query(Evidence).filter(
            Evidence.id == target_id,
            Evidence.case_id == case_id,
        ).first()
        if not ev:
            raise HTTPException(status_code=404, detail="Evidence item not found.")
        target_bytes = ev.content_bytes
        if not target_bytes:
            from backend.utils.file_storage import get_evidence_bytes
            target_bytes = get_evidence_bytes(ev)
        filename = ev.original_filename
        relative_path = ev.original_filename
        size_bytes = ev.file_size_bytes or (len(target_bytes) if target_bytes else 0)
        sha256_hash = ev.sha256
        mime_type = ev.mime_type
        is_derived = False
        source_container = ev.original_filename

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported target_type: {target_type}")

    if target_bytes is None:
        raise HTTPException(status_code=404, detail="Target file buffer is unavailable in storage.")

    # 2. Check if file is an SQLite database
    is_sqlite = target_bytes.startswith(b"SQLite format 3\x00")

    if is_sqlite:
        tmp_db_file = None
        tmp_files_to_clean = []
        conn = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                f.write(target_bytes)
                tmp_db_file = f.name
                tmp_files_to_clean.append(tmp_db_file)

            # If evidence file member, check for companion WAL/SHM in same container
            if target_type == "evidence_file":
                base_rel = ef.relative_path
                wal_ef = db.query(EvidenceFile).filter(
                    EvidenceFile.evidence_id == ef.evidence_id,
                    EvidenceFile.relative_path == f"{base_rel}-wal",
                ).first()
                if wal_ef and wal_ef.content_bytes:
                    try:
                        wal_path = f"{tmp_db_file}-wal"
                        with open(wal_path, "wb") as wf:
                            wf.write(wal_ef.content_bytes)
                        tmp_files_to_clean.append(wal_path)
                    except Exception:
                        pass

                shm_ef = db.query(EvidenceFile).filter(
                    EvidenceFile.evidence_id == ef.evidence_id,
                    EvidenceFile.relative_path == f"{base_rel}-shm",
                ).first()
                if shm_ef and shm_ef.content_bytes:
                    try:
                        shm_path = f"{tmp_db_file}-shm"
                        with open(shm_path, "wb") as sf:
                            sf.write(shm_ef.content_bytes)
                        tmp_files_to_clean.append(shm_path)
                    except Exception:
                        pass

            conn = sqlite3.connect(tmp_db_file)
            cursor = conn.cursor()

            # Query all table names and row counts
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name ASC;")
            raw_tables = cursor.fetchall()

            tables_meta = []
            for t_name, ddl in raw_tables:
                try:
                    c2 = conn.cursor()
                    c2.execute(f'SELECT COUNT(*) FROM "{t_name}";')
                    cnt = c2.fetchone()[0]
                except Exception:
                    cnt = 0
                tables_meta.append({
                    "name": t_name,
                    "row_count": cnt,
                    "sql": ddl or "",
                })

            active_table = table_name_str
            if not active_table or not any(t["name"] == active_table for t in tables_meta):
                active_table = tables_meta[0]["name"] if tables_meta else None

            columns_meta = []
            rows_data = []
            total_rows = 0
            filtered_rows = 0

            if active_table:
                # PRAGMA table_info for columns
                cursor.execute(f'PRAGMA table_info("{active_table}");')
                col_rows = cursor.fetchall()
                columns_meta = [
                    {
                        "cid": col[0],
                        "name": col[1],
                        "type": col[2] or "TEXT",
                        "notnull": bool(col[3]),
                        "dflt_value": col[4],
                        "pk": bool(col[5]),
                    }
                    for col in col_rows
                ]

                # Total count in this table
                for tm in tables_meta:
                    if tm["name"] == active_table:
                        total_rows = tm["row_count"]
                        break

                # Build search WHERE clause if search string provided
                where_clauses = []
                params = []
                if search_str:
                    q = f"%{search_str}%"
                    for col in columns_meta:
                        where_clauses.append(f'CAST("{col["name"]}" AS TEXT) LIKE ?')
                        params.append(q)
                where_sql = f"WHERE {' OR '.join(where_clauses)}" if where_clauses else ""

                # Count rows matching search filter
                cursor.execute(f'SELECT COUNT(*) FROM "{active_table}" {where_sql};', params)
                filtered_rows = cursor.fetchone()[0]

                # Sorting
                order_sql = ""
                col_names = [c["name"] for c in columns_meta]
                if sort_by_str and sort_by_str in col_names:
                    direction = "DESC" if sort_order_str == "desc" else "ASC"
                    order_sql = f'ORDER BY "{sort_by_str}" {direction}'

                # Query paginated rows
                query_params = list(params) + [limit_int, offset_int]
                cursor.execute(
                    f'SELECT * FROM "{active_table}" {where_sql} {order_sql} LIMIT ? OFFSET ?;',
                    query_params,
                )
                raw_rows = cursor.fetchall()

                for r in raw_rows:
                    row_dict = {}
                    for idx, col in enumerate(columns_meta):
                        row_dict[col["name"]] = _clean_text_preview(r[idx], col["name"])
                    rows_data.append(row_dict)

            return {
                "is_database": True,
                "file_type": "sqlite",
                "filename": filename,
                "relative_path": relative_path,
                "size_bytes": size_bytes,
                "sha256": sha256_hash,
                "mime_type": "application/x-sqlite3",
                "source_container": source_container,
                "is_derived": is_derived,
                "table_count": len(tables_meta),
                "tables": tables_meta,
                "selected_table": active_table,
                "columns": columns_meta,
                "rows": rows_data,
                "total_rows": total_rows,
                "filtered_rows": filtered_rows,
                "limit": limit_int,
                "offset": offset_int,
            }

        except sqlite3.Error as err:
            raise HTTPException(
                status_code=400,
                detail=f"SQLite database parsing error: {str(err)}",
            )
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            for fpath in tmp_files_to_clean:
                try:
                    if os.path.exists(fpath):
                        os.unlink(fpath)
                except Exception:
                    pass

    # 3. Non-Database Files: Check category
    cat, spec_type = _detect_file_type(filename, mime_type, target_bytes)

    # Media File Handling (Images, Audio, Video)
    if cat == "media" or (mime_type and any(mime_type.startswith(x) for x in ["image/", "audio/", "video/"])):
        # Determine specific preview MIME
        actual_mime = mime_type
        fn_l = filename.lower()
        if not actual_mime or actual_mime == "application/octet-stream":
            if fn_l.endswith((".jpg", ".jpeg")) or target_bytes.startswith(b"\xff\xd8\xff"):
                actual_mime = "image/jpeg"
                spec_type = "image"
            elif fn_l.endswith(".png") or target_bytes.startswith(b"\x89PNG"):
                actual_mime = "image/png"
                spec_type = "image"
            elif fn_l.endswith(".webp") or b"WEBP" in target_bytes[:16]:
                actual_mime = "image/webp"
                spec_type = "image"
            elif fn_l.endswith(".gif") or target_bytes.startswith(b"GIF8"):
                actual_mime = "image/gif"
                spec_type = "image"
            elif fn_l.endswith(".opus") or target_bytes.startswith(b"OggS"):
                actual_mime = "audio/ogg; codecs=opus"
                spec_type = "audio"
            elif fn_l.endswith((".mp3", ".wav", ".m4a", ".aac")):
                actual_mime = f"audio/{fn_l.split('.')[-1]}"
                spec_type = "audio"
            elif fn_l.endswith((".mp4", ".mov", ".m4v")):
                actual_mime = "video/mp4"
                spec_type = "video"
            else:
                actual_mime = "image/jpeg"
                spec_type = "image"

        media_b64 = None
        if len(target_bytes) < 30 * 1024 * 1024:
            media_b64 = f"data:{actual_mime};base64,{base64.b64encode(target_bytes).decode('ascii')}"

        return {
            "is_database": False,
            "is_media": True,
            "file_type": spec_type,
            "category": "media",
            "filename": filename,
            "relative_path": relative_path,
            "size_bytes": size_bytes,
            "sha256": sha256_hash,
            "mime_type": actual_mime,
            "source_container": source_container,
            "is_derived": is_derived,
            "media_preview": media_b64,
            "media_base64": media_b64,
        }

    # Text, XML, JSON, Log, Config, or Binary
    try:
        raw_text = target_bytes.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        try:
            raw_text = target_bytes.decode("latin-1")
            encoding = "latin-1"
        except Exception:
            raw_text = None
            encoding = "binary"

    if raw_text is not None:
        formatted_content = None
        # Format JSON if valid
        if spec_type == "json" or filename.lower().endswith(".json"):
            try:
                parsed_json = json.loads(raw_text)
                formatted_content = json.dumps(parsed_json, indent=2, ensure_ascii=False)
            except Exception:
                pass
        # Format XML if valid
        elif spec_type == "xml" or filename.lower().endswith(".xml"):
            try:
                dom = xml.dom.minidom.parseString(raw_text)
                formatted_content = dom.toprettyxml(indent="  ")
            except Exception:
                pass

        lines = raw_text.splitlines()

        # If search query is provided for text file, filter lines
        search_matches = []
        if search_str:
            q = search_str.lower()
            for line_no, line in enumerate(lines, 1):
                if q in line.lower():
                    search_matches.append({"line_number": line_no, "text": line})

        return {
            "is_database": False,
            "is_media": False,
            "file_type": spec_type,
            "category": cat,
            "filename": filename,
            "relative_path": relative_path,
            "size_bytes": size_bytes,
            "sha256": sha256_hash,
            "mime_type": mime_type or "text/plain",
            "source_container": source_container,
            "is_derived": is_derived,
            "content_text": raw_text,
            "formatted_content": formatted_content,
            "line_count": len(lines),
            "encoding": encoding,
            "search_matches": search_matches if search_str else None,
        }

    # Pure binary fallback -> hex dump
    hex_dump = _generate_hex_dump(target_bytes)
    return {
        "is_database": False,
        "is_media": False,
        "file_type": "binary",
        "category": "other",
        "filename": filename,
        "relative_path": relative_path,
        "size_bytes": size_bytes,
        "sha256": sha256_hash,
        "mime_type": mime_type or "application/octet-stream",
        "source_container": source_container,
        "is_derived": is_derived,
        "hex_dump": hex_dump,
    }
