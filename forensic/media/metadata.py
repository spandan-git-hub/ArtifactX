"""Metadata extraction for media files."""

from pathlib import Path
from typing import Dict, Any, Optional

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from image files including EXIF data.

    Args:
        file_path: Path to the image file

    Returns:
        Dictionary containing width, height, and exif_data
    """
    if not PIL_AVAILABLE:
        return {"width": None, "height": None, "exif_data": {}}

    if not file_path.exists():
        return {"width": None, "height": None, "exif_data": {}}

    try:
        with Image.open(file_path) as img:
            width, height = img.size

            # Extract EXIF data
            exif_data = {}
            if hasattr(img, '_getexif') and img._getexif() is not None:
                for tag_id, value in img._getexif().items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value

            return {
                "width": width,
                "height": height,
                "exif_data": exif_data
            }
    except Exception:
        # If we can't read the image, return None values
        return {"width": None, "height": None, "exif_data": {}}


def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from video files.
    For now, returns placeholder values since we don't have video processing libraries.
    In a production implementation, this would use libraries like opencv, ffmpeg-python, or mediainfo.

    Args:
        file_path: Path to the video file

    Returns:
        Dictionary containing width, height, and duration
    """
    # Placeholder implementation - in production would use video processing libraries
    return {
        "width": None,
        "height": None,
        "duration": None
    }


def extract_audio_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from audio files.
    For now, returns placeholder values since we don't have audio processing libraries.
    In a production implementation, this would use libraries like mutagen, pydub, or ffmpeg.

    Args:
        file_path: Path to the audio file

    Returns:
        Dictionary containing duration
    """
    # Placeholder implementation - in production would use audio processing libraries
    return {
        "duration": None
    }


def extract_media_metadata(file_path: Path, media_type: str) -> Dict[str, Any]:
    """
    Extract metadata from media files based on media type.

    Args:
        file_path: Path to the media file
        media_type: One of "image", "video", "audio", "document", "other"

    Returns:
        Dictionary containing metadata appropriate for the media type
    """
    if not file_path.exists():
        return {}

    if media_type == "image":
        return extract_image_metadata(file_path)
    elif media_type == "video":
        return extract_video_metadata(file_path)
    elif media_type == "audio":
        return extract_audio_metadata(file_path)
    else:
        # For documents and other files, we don't extract specific metadata for now
        return {}