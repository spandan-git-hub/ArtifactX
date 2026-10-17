"""
In-memory archive unpacking and exhibit binding for forensic packages (spec 11_PIPELINE_AND_E2E.md, STEPS.md Phase 1).

Expands application packages (com.whatsapp.zip, org.telegram.messenger.zip, ArtifactX_Synthetic_Input_v1.zip)
into typed in-memory EvidenceInput exhibits without disk writes (Rule R4, Rule R12).
Extracts radioactive cryptographic key material safely into KeyMaterial containers (Rule R5).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional, Sequence, Set, Tuple
import zipfile

from forensic.common.hashing import sha256_hex
from forensic.decryption.whatsapp.types import KeyMaterial
from forensic.pipeline.models import EvidenceInput


def unpack_evidence_inputs(
    inputs: Sequence[EvidenceInput],
    keys: Sequence[KeyMaterial] = (),
    max_unpacked_bytes: int = 256 * 1024 * 1024,
) -> Tuple[List[EvidenceInput], List[KeyMaterial]]:
    """
    Safely expand container archives in-memory into individual evidence inputs.
    Discovers primary databases, WAL logs, contact databases, media, and key files.

    Guarantees:
    - Pure in-memory transformation; zero disk writes (Rule R4).
    - Capped member count and size checks against ZIP bombs/traversal (Rule R12).
    - Keys parsed safely into KeyMaterial without logging raw secret bytes (Rule R5).
    - Preserves parent archive exhibits so stage 1 integrity verification covers whole archives.
    """
    expanded_inputs: List[EvidenceInput] = []
    discovered_keys: List[KeyMaterial] = list(keys)
    seen_key_fps: Set[str] = {k.fingerprint() for k in discovered_keys}

    for inp in inputs:
        # Retain parent exhibit in the pipeline working set
        expanded_inputs.append(inp)

        # Check if input is a ZIP container
        is_zip = (
            inp.data.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
            or inp.name.lower().endswith(".zip")
            or inp.role in ("media_zip", "archive")
        )
        if not is_zip:
            continue

        try:
            with zipfile.ZipFile(io.BytesIO(inp.data), "r") as zf:
                # Cap member inspection to 1000 items (Rule R12)
                infos = zf.infolist()[:1000]
                for info in infos:
                    if info.is_dir():
                        continue

                    # Path traversal safety (Rule R12)
                    rel_name = info.filename.replace("\\", "/")
                    if rel_name.startswith("../") or "/../" in rel_name or rel_name.startswith("/"):
                        continue

                    # Size safety limit
                    if info.file_size > max_unpacked_bytes:
                        continue

                    member_bytes = zf.read(info.filename)
                    if len(member_bytes) > max_unpacked_bytes:
                        continue

                    m_hash = sha256_hex(member_bytes)
                    base_name = Path(info.filename).name.lower()
                    m_lower = info.filename.lower()

                    # Classify role
                    role = "other"
                    if base_name == "key" or base_name.endswith(".key"):
                        role = "key_file"
                        # Extract KeyMaterial safely
                        km: Optional[KeyMaterial] = None
                        if len(member_bytes) == 158:
                            km = KeyMaterial(key_file_bytes=member_bytes, key_type="crypt14")
                        elif len(member_bytes) in (32, 59, 64):
                            km = KeyMaterial(key_file_bytes=member_bytes, key_type="crypt15")
                        elif len(member_bytes) > 0:
                            km = KeyMaterial(key_file_bytes=member_bytes, key_type="auto")

                        if km and km.fingerprint() not in seen_key_fps:
                            seen_key_fps.add(km.fingerprint())
                            discovered_keys.append(km)

                    elif "passcode" in base_name and base_name.endswith(".txt"):
                        role = "key_file"
                        for line in member_bytes.decode("utf-8", errors="ignore").splitlines():
                            clean_line = line.strip()
                            if clean_line and not clean_line.startswith("#") and not clean_line.startswith("SYNTHETIC"):
                                km = KeyMaterial(raw_key=clean_line.encode("utf-8"), key_type="passcode")
                                if km.fingerprint() not in seen_key_fps:
                                    seen_key_fps.add(km.fingerprint())
                                    discovered_keys.append(km)
                                break

                    elif any(base_name.endswith(ext) for ext in (".crypt14", ".crypt15", ".crypt12")):
                        role = "primary"
                    elif "msgstore.db" in base_name and not any(base_name.endswith(ext) for ext in ("-wal", "-shm")):
                        role = "primary"
                    elif "cache4.db" in base_name and not any(base_name.endswith(ext) for ext in ("-wal", "-shm")):
                        role = "primary"
                    elif "tdata" in m_lower or base_name in ("key_datas", "maps") or base_name.startswith("d877f783d5d3ef8c") or "messagess" in base_name:
                        role = "primary"
                    elif base_name in ("wa.db", "contacts.db"):
                        role = "wa_contacts"
                    elif base_name.endswith("-wal"):
                        role = "wal"
                    elif base_name.endswith("-shm"):
                        role = "shm"
                    elif any(base_name.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".ogg", ".mp3", ".wav")):
                        role = "other"

                    sub_id = f"{inp.evidence_id}:{info.filename}"
                    expanded_inputs.append(
                        EvidenceInput(
                            evidence_id=sub_id,
                            sha256=m_hash,
                            name=info.filename,
                            data=member_bytes,
                            role=role,
                        )
                    )

                    # Handle 1 level of nested archives (e.g. UPLOAD_TELEGRAM_TDATA.zip)
                    if base_name.endswith(".zip") and len(member_bytes) < max_unpacked_bytes:
                        try:
                            with zipfile.ZipFile(io.BytesIO(member_bytes), "r") as sub_zf:
                                for sub_info in sub_zf.infolist()[:500]:
                                    if sub_info.is_dir():
                                        continue
                                    sub_rel = sub_info.filename.replace("\\", "/")
                                    if sub_rel.startswith("../") or "/../" in sub_rel or sub_rel.startswith("/"):
                                        continue
                                    if sub_info.file_size > max_unpacked_bytes:
                                        continue
                                    sub_bytes = sub_zf.read(sub_info.filename)
                                    sub_hash = sha256_hex(sub_bytes)
                                    sub_bname = Path(sub_info.filename).name.lower()
                                    sub_mlower = sub_info.filename.lower()
                                    sub_role = "other"
                                    if "tdata" in sub_mlower or sub_bname in ("key_datas", "maps") or sub_bname.startswith("d877f783d5d3ef8c") or "messagess" in sub_bname:
                                        sub_role = "primary"
                                    elif "msgstore.db" in sub_bname and not any(sub_bname.endswith(x) for x in ("-wal", "-shm")):
                                        sub_role = "primary"
                                    elif "cache4.db" in sub_bname and not any(sub_bname.endswith(x) for x in ("-wal", "-shm")):
                                        sub_role = "primary"
                                    elif sub_bname in ("wa.db", "contacts.db"):
                                        sub_role = "wa_contacts"
                                    elif sub_bname.endswith("-wal"):
                                        sub_role = "wal"
                                    elif sub_bname.endswith("-shm"):
                                        sub_role = "shm"

                                    expanded_inputs.append(
                                        EvidenceInput(
                                            evidence_id=f"{sub_id}:{sub_info.filename}",
                                            sha256=sub_hash,
                                            name=sub_info.filename,
                                            data=sub_bytes,
                                            role=sub_role,
                                        )
                                    )
                        except Exception:
                            pass
        except Exception:
            # Corrupt or unreadable zip fails safe without interrupting other inputs
            continue

    return expanded_inputs, discovered_keys
