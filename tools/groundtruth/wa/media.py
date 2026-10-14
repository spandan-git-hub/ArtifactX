"""Pillow-based deterministic media generator for WhatsApp fixtures.

Follows master.md R11 and 02_GROUND_TRUTH_DATASETS.md B1.3:
- Real small JPEG/PNG images (128x128).
- Deterministic geometric patterns derived strictly from seeded RNG.
- EXIF metadata variants:
  1. Naive DateTimeOriginal only.
  2. DateTimeOriginal + OffsetTimeOriginal.
  3. DateTimeOriginal + full GPS IFD coordinates & GPS time.
"""

import hashlib
import io
from dataclasses import dataclass
from typing import Optional, Tuple
from PIL import Image, ImageDraw
from PIL.ExifTags import Base, IFD
from PIL.TiffImagePlugin import IFDRational

from tools.groundtruth.rng import DeterministicRNG


@dataclass
class GeneratedMediaFile:
    filename: str
    relative_path: str
    content_bytes: bytes
    sha256: str
    size: int
    mime_type: str
    width: int
    height: int
    exif_type: str              # none, naive_dt, offset_dt, gps_dt
    gps_coords: Optional[Tuple[float, float]] = None


def _to_deg_min_sec(val: float) -> Tuple[IFDRational, IFDRational, IFDRational]:
    """Convert decimal coordinate to (degrees, minutes, seconds) IFDRationals."""
    abs_val = abs(val)
    deg = int(abs_val)
    rem = (abs_val - deg) * 60
    min_ = int(rem)
    sec = round((rem - min_) * 60, 2)
    sec_num = int(round(sec * 100))
    return (
        IFDRational(deg, 1),
        IFDRational(min_, 1),
        IFDRational(sec_num, 100),
    )


def generate_deterministic_image(
    rng: DeterministicRNG,
    filename: str,
    relative_path: str,
    img_type: str = "jpeg",
    exif_variant: str = "none",
    width: int = 128,
    height: int = 128,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> GeneratedMediaFile:
    """Generate a small deterministic image with colored patterns and optional EXIF."""
    # Create image canvas
    bg_r = rng.randint(40, 220)
    bg_g = rng.randint(40, 220)
    bg_b = rng.randint(40, 220)
    img = Image.new("RGB", (width, height), color=(bg_r, bg_g, bg_b))
    draw = ImageDraw.Draw(img)

    # Draw geometric patterns deterministically
    for _ in range(5):
        x0 = rng.randint(5, width - 40)
        y0 = rng.randint(5, height - 40)
        x1 = x0 + rng.randint(15, 35)
        y1 = y0 + rng.randint(15, 35)
        fill = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
        shape = rng.choice(["rectangle", "ellipse"])
        if shape == "rectangle":
            draw.rectangle([x0, y0, x1, y1], fill=fill)
        else:
            draw.ellipse([x0, y0, x1, y1], fill=fill)

    buf = io.BytesIO()
    gps_coords = None

    if img_type.lower() == "png":
        img.save(buf, format="PNG")
        mime = "image/png"
    else:
        mime = "image/jpeg"
        exif = img.getexif()

        if exif_variant == "naive_dt":
            # 1. Naive DateTimeOriginal only (no timezone offset)
            exif[Base.DateTimeOriginal] = "2026:09:15 14:30:00"
        elif exif_variant == "offset_dt":
            # 2. DateTimeOriginal + OffsetTimeOriginal
            exif[Base.DateTimeOriginal] = "2026:09:16 10:15:00"
            exif[Base.OffsetTimeOriginal] = "+05:30"
        elif exif_variant == "gps_dt":
            # 3. Full GPS IFD tags
            exif[Base.DateTimeOriginal] = "2026:09:17 11:45:00"
            gps_ifd = exif.get_ifd(IFD.GPSInfo)
            target_lat = lat if lat is not None else 18.921984
            target_lon = lon if lon is not None else 72.834654
            gps_coords = (target_lat, target_lon)

            gps_ifd[1] = "N" if target_lat >= 0 else "S"
            gps_ifd[2] = _to_deg_min_sec(target_lat)
            gps_ifd[3] = "E" if target_lon >= 0 else "W"
            gps_ifd[4] = _to_deg_min_sec(target_lon)
            gps_ifd[7] = (IFDRational(6, 1), IFDRational(15, 1), IFDRational(0, 1))  # 06:15:00 UTC
            gps_ifd[29] = "2026:09:17"

        img.save(buf, format="JPEG", exif=exif, quality=85)

    data = buf.getvalue()
    sha256 = hashlib.sha256(data).hexdigest()

    return GeneratedMediaFile(
        filename=filename,
        relative_path=relative_path,
        content_bytes=data,
        sha256=sha256,
        size=len(data),
        mime_type=mime,
        width=width,
        height=height,
        exif_type=exif_variant,
        gps_coords=gps_coords,
    )
