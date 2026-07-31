"""Metadata extraction for media files."""

from pathlib import Path
from typing import Dict, Any, Optional

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _convert_to_degrees(value) -> float:
    """Convert GPS degree/minute/second tuple or IFD tag value to decimal degrees."""
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if hasattr(value, '__len__') and len(value) == 3:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 360.0)
    except Exception:
        pass
    return 0.0


def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from image files including EXIF data, camera details, and GPS.

    Args:
        file_path: Path to the image file

    Returns:
        Dictionary containing width, height, camera details, GPS, and sanitized exif_data
    """
    if not PIL_AVAILABLE or not file_path.exists():
        return {
            "width": None,
            "height": None,
            "exif_data": {},
            "camera": {},
            "gps": {"has_gps": False},
        }

    try:
        with Image.open(file_path) as img:
            width, height = img.size
            raw_exif = {}
            sanitized_exif = {}
            gps_info = {}

            if hasattr(img, '_getexif') and img._getexif() is not None:
                for tag_id, value in img._getexif().items():
                    tag = TAGS.get(tag_id, tag_id)
                    raw_exif[tag] = value

                    # Stringify non-serializable objects for JSON
                    if isinstance(value, bytes):
                        try:
                            sanitized_exif[str(tag)] = value.decode('utf-8', errors='ignore')
                        except Exception:
                            sanitized_exif[str(tag)] = str(value)
                    elif isinstance(value, (tuple, list)):
                        sanitized_exif[str(tag)] = [str(v) if not isinstance(v, (int, float, str)) else v for v in value]
                    elif isinstance(value, (int, float, str, bool)):
                        sanitized_exif[str(tag)] = value
                    else:
                        sanitized_exif[str(tag)] = str(value)

                    if tag == "GPSInfo" and isinstance(value, dict):
                        gps_info = value

            # Extract structured camera details
            camera = {
                "make": str(raw_exif.get("Make", "")).strip() or None,
                "model": str(raw_exif.get("Model", "")).strip() or None,
                "software": str(raw_exif.get("Software", "")).strip() or None,
                "date_time": str(raw_exif.get("DateTimeOriginal") or raw_exif.get("DateTime", "")).strip() or None,
                "iso": raw_exif.get("ISOSpeedRatings"),
                "f_number": str(raw_exif.get("FNumber")) if raw_exif.get("FNumber") else None,
                "focal_length": str(raw_exif.get("FocalLength")) if raw_exif.get("FocalLength") else None,
                "exposure_time": str(raw_exif.get("ExposureTime")) if raw_exif.get("ExposureTime") else None,
            }

            # Parse GPS data if available (Tag 1 = LatRef, Tag 2 = Lat, Tag 3 = LongRef, Tag 4 = Long, Tag 6 = Alt)
            gps_data = {"has_gps": False, "latitude": None, "longitude": None, "altitude": None, "map_url": None}
            if gps_info:
                try:
                    lat_val = gps_info.get(2)
                    lat_ref = gps_info.get(1)
                    lng_val = gps_info.get(4)
                    lng_ref = gps_info.get(3)
                    alt_val = gps_info.get(6)

                    if lat_val and lng_val:
                        lat = _convert_to_degrees(lat_val)
                        if lat_ref and str(lat_ref).upper() == 'S':
                            lat = -lat
                        lng = _convert_to_degrees(lng_val)
                        if lng_ref and str(lng_ref).upper() == 'W':
                            lng = -lng
                        
                        alt = float(alt_val) if alt_val else None

                        gps_data = {
                            "has_gps": True,
                            "latitude": round(lat, 6),
                            "longitude": round(lng, 6),
                            "altitude": alt,
                            "map_url": f"https://www.google.com/maps?q={lat},{lng}",
                            "osm_url": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=15/{lat}/{lng}"
                        }
                except Exception:
                    pass

            return {
                "width": width,
                "height": height,
                "camera": camera,
                "gps": gps_data,
                "exif_data": sanitized_exif,
            }
    except Exception:
        return {
            "width": None,
            "height": None,
            "exif_data": {},
            "camera": {},
            "gps": {"has_gps": False},
        }


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