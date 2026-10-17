"""File storage utilities for keeping uploaded files on local disk (in uploads directory)."""

import os
import shutil
from pathlib import Path
from typing import Any, Optional, Union

from backend.app.config import BASE_DIR, UPLOADS_DIR


def ensure_directory(path: Union[Path, str]) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_upload(file_name: str, file_data: bytes, subfolder: Optional[str] = None) -> Path:
    """Save raw file bytes to disk under the uploads directory.

    Args:
        file_name: Name of file (should be sanitized/unique).
        file_data: Raw bytes to persist.
        subfolder: Optional subfolder within UPLOADS_DIR (e.g. for case or extraction).

    Returns:
        Absolute Path to saved file.
    """
    dest_dir = UPLOADS_DIR / subfolder if subfolder else UPLOADS_DIR
    ensure_directory(dest_dir)
    dest_path = dest_dir / file_name
    dest_path.write_bytes(file_data)
    return dest_path


def create_extract_dir(dir_name: Optional[str] = None, subfolder: Optional[str] = None) -> Path:
    """Create a new extraction directory in uploads under an optional subfolder (e.g. case number)."""
    import uuid
    name = dir_name or f"extract_{uuid.uuid4().hex}"
    parent = UPLOADS_DIR / subfolder if subfolder else UPLOADS_DIR
    dest = parent / name
    ensure_directory(dest)
    return dest


def save_extracted_members(extract_dir: Path, members: list) -> None:
    """Save extracted ZIP member files to disk in extract_dir."""
    ensure_directory(extract_dir)
    for member in members:
        norm_path = getattr(member, "normalized_path", None)
        content = getattr(member, "content_bytes", None)
        if norm_path is None and isinstance(member, dict):
            norm_path = member.get("relative_path")
            content = member.get("content_bytes")
        if norm_path and content is not None:
            # Replace characters illegal on Windows filesystems (e.g. :: for nested zip members)
            safe_rel = norm_path.replace("::", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
            dest = extract_dir / safe_rel
            ensure_directory(dest.parent)
            dest.write_bytes(content)


def delete_file(filepath: Union[Path, str, None]) -> None:
    """Delete a file or directory from storage if it exists on disk."""
    if not filepath or str(filepath).startswith("db://"):
        return
    try:
        p = Path(filepath)
        if not p.is_absolute():
            # Try resolving against UPLOADS_DIR or BASE_DIR
            candidate = UPLOADS_DIR / p
            if candidate.exists():
                p = candidate
            else:
                candidate_base = BASE_DIR / p
                if candidate_base.exists():
                    p = candidate_base
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
    except Exception:
        pass


def resolve_evidence_path(storage_path: Optional[str]) -> Optional[Path]:
    """Resolve an Evidence storage_path to an existing file or directory on disk.

    Handles absolute paths, paths relative to UPLOADS_DIR, paths relative to BASE_DIR,
    or bare filenames.
    """
    if not storage_path or str(storage_path).startswith("db://"):
        return None
    try:
        p = Path(storage_path)
        if p.is_file() or p.is_dir():
            return p

        # Check UPLOADS_DIR / bare filename
        c1 = UPLOADS_DIR / p.name
        if c1.is_file() or c1.is_dir():
            return c1

        # Check UPLOADS_DIR / relative path
        c2 = UPLOADS_DIR / p
        if c2.is_file() or c2.is_dir():
            return c2

        # Check BASE_DIR / path
        c3 = BASE_DIR / p
        if c3.is_file() or c3.is_dir():
            return c3
    except Exception:
        pass
    return None


def resolve_evidence_file_path(evidence_file: Any) -> Optional[Path]:
    """Resolve an EvidenceFile instance to an existing file on disk."""
    if not evidence_file:
        return None

    rel_path = getattr(evidence_file, "relative_path", None)
    if not rel_path:
        return None

    # 1. If parent evidence has extracted_path, look in extracted_path
    evidence = getattr(evidence_file, "evidence", None)
    if evidence:
        safe_rel = rel_path.replace("::", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
        ext_path = getattr(evidence, "extracted_path", None)
        if ext_path and not str(ext_path).startswith("db://"):
            resolved_ext = resolve_evidence_path(ext_path)
            if resolved_ext and resolved_ext.is_dir():
                candidate = resolved_ext / rel_path
                if candidate.is_file():
                    return candidate
                candidate_safe = resolved_ext / safe_rel
                if candidate_safe.is_file():
                    return candidate_safe

        # If not zip or no extracted_path, check parent storage_path directory
        st_path = getattr(evidence, "storage_path", None)
        if st_path and not str(st_path).startswith("db://"):
            resolved_st = resolve_evidence_path(st_path)
            if resolved_st:
                base_dir = resolved_st if resolved_st.is_dir() else resolved_st.parent
                candidate = base_dir / rel_path
                if candidate.is_file():
                    return candidate
                candidate_safe = base_dir / safe_rel
                if candidate_safe.is_file():
                    return candidate_safe

    # 2. Check directly under UPLOADS_DIR
    c1 = UPLOADS_DIR / rel_path
    if c1.is_file():
        return c1

    c2 = UPLOADS_DIR / Path(rel_path).name
    if c2.is_file():
        return c2

    return None


def get_evidence_bytes(evidence: Any) -> Optional[bytes]:
    """Retrieve raw file bytes for Evidence from in-memory bytes or disk in uploads."""
    if evidence is None:
        return None

    # Check internal byte column if already loaded
    internal_bytes = getattr(evidence, "_content_bytes", None)
    if internal_bytes is not None:
        return internal_bytes

    # Check property
    cb = getattr(evidence, "content_bytes", None)
    if cb is not None:
        return cb

    # Resolve from disk
    p = resolve_evidence_path(getattr(evidence, "storage_path", None))
    if p and p.is_file():
        try:
            return p.read_bytes()
        except Exception:
            return None
    return None


def get_evidence_file_bytes(evidence_file: Any) -> Optional[bytes]:
    """Retrieve raw file bytes for EvidenceFile from in-memory bytes or disk in uploads."""
    if evidence_file is None:
        return None

    internal_bytes = getattr(evidence_file, "_content_bytes", None)
    if internal_bytes is not None:
        return internal_bytes

    cb = getattr(evidence_file, "content_bytes", None)
    if cb is not None:
        return cb

    p = resolve_evidence_file_path(evidence_file)
    if p and p.is_file():
        try:
            return p.read_bytes()
        except Exception:
            return None
    return None
