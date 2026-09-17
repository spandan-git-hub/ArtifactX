"""File storage utilities."""

import shutil
from pathlib import Path

from backend.app.config import UPLOADS_DIR


from typing import Union

def save_upload(file_name: str, file_data: bytes) -> Path:
    """Legacy save function. In Phase C, uploads are persisted directly into PostgreSQL."""
    dest = UPLOADS_DIR / file_name
    return dest


def delete_file(filepath: Union[Path, str]) -> None:
    """Delete a file or directory from storage if it exists on disk."""
    if not filepath or str(filepath).startswith("db://"):
        return
    try:
        p = Path(filepath)
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    except Exception:
        pass


def ensure_directory(path: str) -> None:
    """Ensure a directory exists, creating it if necessary."""
    import os
    os.makedirs(path, exist_ok=True)
