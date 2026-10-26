"""File storage utilities for keeping uploaded files on local disk (in uploads directory)."""

import os
import re
import shutil
import stat
from pathlib import Path
from typing import Any, List, Optional, Union

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


def _handle_remove_readonly(func, path, exc_info):
    """Clear Windows readonly attribute and retry deletion."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


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
                try:
                    shutil.rmtree(p, onerror=_handle_remove_readonly)
                except Exception:
                    shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    os.chmod(p, stat.S_IWRITE)
                except Exception:
                    pass
                p.unlink(missing_ok=True)
    except Exception:
        pass


def cleanup_case_disk_data(
    case_id: int,
    case_number: Optional[str] = None,
    extra_paths: Optional[List[Union[Path, str, None]]] = None,
) -> None:
    """Thoroughly remove all local disk directories and files associated with a case."""
    if extra_paths:
        for ep in extra_paths:
            if ep:
                delete_file(ep)

    target_names = set()
    if case_number:
        target_names.add(str(case_number))
        target_names.add(re.sub(r'[^\w\-.]', '_', str(case_number)))
    target_names.add(f"case_{case_id}")
    target_names.add(str(case_id))

    for name in target_names:
        case_dir = UPLOADS_DIR / name
        if case_dir.exists():
            delete_file(case_dir)


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

        # Check UPLOADS_DIR / path
        c3 = BASE_DIR / p
        if c3.is_file() or c3.is_dir():
            return c3

        # Check inside subdirectories of UPLOADS_DIR (e.g. case folders uploads/ARX-2026-001/...)
        for sub in UPLOADS_DIR.iterdir():
            if sub.is_dir():
                sub_p = sub / p.name
                if sub_p.is_file() or sub_p.is_dir():
                    return sub_p
                sub_rel = sub / p
                if sub_rel.is_file() or sub_rel.is_dir():
                    return sub_rel
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

    # 3. Check inside case folders / extract folders under UPLOADS_DIR
    norm_name = Path(rel_path).name
    safe_rel = rel_path.replace("::", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
    for case_sub in UPLOADS_DIR.iterdir():
        if case_sub.is_dir():
            sub_cand = case_sub / rel_path
            if sub_cand.is_file():
                return sub_cand
            sub_cand_safe = case_sub / safe_rel
            if sub_cand_safe.is_file():
                return sub_cand_safe
            sub_name = case_sub / norm_name
            if sub_name.is_file():
                return sub_name
            # Check extract_* subdirectories inside case folder
            for sub_extract in case_sub.glob("extract_*"):
                if sub_extract.is_dir():
                    ext_cand = sub_extract / rel_path
                    if ext_cand.is_file():
                        return ext_cand
                    ext_cand_safe = sub_extract / safe_rel
                    if ext_cand_safe.is_file():
                        return ext_cand_safe
                    ext_cand_name = sub_extract / norm_name
                    if ext_cand_name.is_file():
                        return ext_cand_name

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
    """Retrieve raw file bytes for EvidenceFile from in-memory bytes, disk in uploads, or parent archive."""
    if evidence_file is None:
        return None

    internal_bytes = getattr(evidence_file, "_content_bytes", None)
    if internal_bytes is not None:
        return internal_bytes

    p = resolve_evidence_file_path(evidence_file)
    if p and p.is_file():
        try:
            return p.read_bytes()
        except Exception:
            pass

    # If the file record exists with file_size == 0 or empty hash, return empty bytes
    sha = getattr(evidence_file, "sha256", None)
    f_size = getattr(evidence_file, "file_size", None)
    if f_size == 0 or sha == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
        return b""

    # Fallback to parent evidence archive if zip
    evidence = getattr(evidence_file, "evidence", None)
    if evidence:
        ev_b = get_evidence_bytes(evidence)
        if ev_b and ev_b.startswith(b"PK\x03\x04"):
            import io, zipfile
            try:
                with zipfile.ZipFile(io.BytesIO(ev_b)) as z:
                    rel_path = getattr(evidence_file, "relative_path", "")
                    clean_rel = rel_path.replace("\\", "/")
                    if clean_rel in z.namelist():
                        return z.read(clean_rel)
                    for name in z.namelist():
                        if name.endswith(clean_rel) or clean_rel.endswith(name):
                            return z.read(name)
            except Exception:
                pass

    cb = getattr(evidence_file, "content_bytes", None)
    if cb is not None:
        return cb

    return None
