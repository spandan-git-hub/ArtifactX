"""File storage utilities."""

import shutil
from pathlib import Path

from backend.app.config import UPLOADS_DIR


def save_upload(file_name: str, file_data: bytes) -> Path:
    """Save uploaded file to storage."""
    dest = UPLOADS_DIR / file_name
    with open(dest, "wb") as f:
        f.write(file_data)
    return dest


def delete_file(filepath: Path) -> None:
    """Delete a file from storage."""
    if filepath.exists():
        if filepath.is_dir():
            shutil.rmtree(filepath)
        else:
            filepath.unlink()
