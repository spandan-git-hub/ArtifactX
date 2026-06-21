"""Media type detection for forensic analysis."""

import mimetypes
from pathlib import Path
from typing import Literal, Optional

# Initialize mimetypes
mimetypes.init()


def detect_media_type(file_path: Path) -> Optional[Literal["image", "video", "audio", "document", "other"]]:
    """
    Detect the media type of a file based on its MIME type and extension.

    Args:
        file_path: Path to the file to analyze

    Returns:
        One of: "image", "video", "audio", "document", "other", or None if file doesn't exist
    """
    if not file_path.exists() or not file_path.is_file():
        return None

    # Get MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))

    if mime_type:
        if mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("video/"):
            return "video"
        elif mime_type.startswith("audio/"):
            return "audio"
        elif mime_type.startswith("text/") or mime_type in [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]:
            return "document"

    # Fallback to extension-based detection for common media types
    extension = file_path.suffix.lower()
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic", ".heif"}
    video_extensions = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".3g2"}
    audio_extensions = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".aiff", ".alac"}

    if extension in image_extensions:
        return "image"
    elif extension in video_extensions:
        return "video"
    elif extension in audio_extensions:
        return "audio"
    elif extension in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".rtf"}:
        return "document"
    else:
        return "other"