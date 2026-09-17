"""Media type detection for forensic analysis."""

import mimetypes
from pathlib import Path
from typing import BinaryIO, Literal, Optional, Union

# Initialize mimetypes
mimetypes.init()


def detect_media_type(
    file_source: Union[Path, str, bytes, BinaryIO],
    filename: Optional[str] = None,
) -> Optional[Literal["image", "video", "audio", "document", "other"]]:
    """
    Detect the media type of a file or in-memory buffer based on its MIME type,
    extension, or magic header bytes.
    """
    name_to_check = filename or ""
    if isinstance(file_source, (str, Path)):
        name_to_check = str(file_source)
    elif isinstance(file_source, bytes):
        if file_source.startswith(b"\xff\xd8\xff") or file_source.startswith(b"\x89PNG") or file_source.startswith(b"GIF8") or file_source.startswith(b"RIFF") and b"WEBP" in file_source[:16]:
            return "image"
        if file_source.startswith(b"%PDF-"):
            return "document"

    # Get MIME type
    mime_type, _ = mimetypes.guess_type(name_to_check)

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