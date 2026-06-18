from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BASE_DIR / "storage" / "evidence"


def safe_filename(filename: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in filename)
    cleaned = cleaned.strip().replace(" ", "_")
    return cleaned or "evidence.txt"


async def save_upload(file: UploadFile, case_id: str) -> tuple[Path, str, int]:
    case_dir = STORAGE_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    destination = case_dir / f"{uuid4().hex}_{safe_filename(file.filename or 'evidence.txt')}"
    digest = sha256()
    size = 0

    with destination.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
            handle.write(chunk)

    await file.seek(0)
    return destination, digest.hexdigest(), size
