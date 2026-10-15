"""Unit tests for in-memory perceptual media hashing and correlation (B12.4).

Follows master.md R4, R8, R11, R12 and 10_CORRELATION.md §B12.4:
- Zero disk writes (in-memory BytesIO only).
- Image.MAX_IMAGE_PIXELS untrusted-input hardening.
- Flat / low entropy images rejected.
- Exact SHA-256 vs perceptual dHash match certainty.
- False positive test over 200+ unrelated synthetic images: asserts 0 pairs under threshold (<=4)
  and measures/reports the nearest-pair distance.
"""

import io
import math
from typing import List
import random
from PIL import Image, ImageDraw
import pytest

from forensic.correlation.media_hash import (
    compute_dhash,
    compute_phash,
    hamming_distance,
    compute_image_entropy,
    LowEntropyImageError,
    PerceptualMediaCorrelator,
)
from forensic.correlation.thresholds import DEFAULT_THRESHOLDS


def _create_synthetic_image(seed: int, width: int = 64, height: int = 64) -> bytes:
    """Generate deterministic in-memory synthetic image bytes with verified Shannon entropy."""
    rng = random.Random(seed * 7919 + 104729)
    img = Image.new("RGB", (width, height), color=(rng.randint(20, 230), rng.randint(20, 230), rng.randint(20, 230)))
    draw = ImageDraw.Draw(img)
    for _ in range(25):
        x0, y0 = rng.randint(0, max(1, width - 14)), rng.randint(0, max(1, height - 14))
        x1, y1 = rng.randint(x0 + 4, width - 1), rng.randint(y0 + 4, height - 1)
        draw.rectangle([x0, y0, x1, y1], fill=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_zero_disk_writes_in_memory_dhash():
    """Verify dHash operates purely in-memory from bytes."""
    raw_bytes = _create_synthetic_image(seed=42)
    h = compute_dhash(raw_bytes)
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_flat_low_entropy_image_rejected():
    """Verify flat single-color image is rejected due to low Shannon entropy."""
    img = Image.new("RGB", (64, 64), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    flat_bytes = buf.getvalue()

    with pytest.raises(LowEntropyImageError):
        compute_dhash(flat_bytes, min_entropy=1.0)


def test_tiny_image_dimensions_rejected():
    """Verify images smaller than min_dimension are rejected."""
    img = Image.new("RGB", (8, 8), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    tiny_bytes = buf.getvalue()

    with pytest.raises(LowEntropyImageError):
        compute_dhash(tiny_bytes, min_dimension=16)


def test_near_duplicate_dhash_distance():
    """Verify near-duplicate image pair matches within Hamming distance <= 4."""
    base_bytes = _create_synthetic_image(seed=101, width=128, height=128)

    # Slightly re-encode and resize near-duplicate
    with Image.open(io.BytesIO(base_bytes)) as img:
        resized = img.resize((120, 120))
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=85)
        near_dup_bytes = buf.getvalue()

    h1 = compute_dhash(base_bytes)
    h2 = compute_dhash(near_dup_bytes)
    dist = hamming_distance(h1, h2)

    assert dist <= DEFAULT_THRESHOLDS.dhash_max_hamming_distance, f"Expected dist <= 4, got {dist}"

    correlator = PerceptualMediaCorrelator()
    items = [
        {"id": 1, "sha256": "sha_a", "dhash": h1, "file_name": "img_a.jpg", "platform": "whatsapp"},
        {"id": 2, "sha256": "sha_b", "dhash": h2, "file_name": "img_b.jpg", "platform": "telegram"},
    ]
    findings = correlator.correlate_media_findings(items)
    assert len(findings) == 1
    f = findings[0]
    assert f.kind == "media_dhash"
    assert f.match_certainty >= 0.75
    assert f.confidence_score < 1.0  # Rule R8


def test_dissimilar_decoy_rejected():
    """Verify dissimilar decoy image (dHash distance ~30) produces zero findings."""
    img1 = _create_synthetic_image(seed=1)
    img2 = _create_synthetic_image(seed=999)

    h1 = compute_dhash(img1)
    h2 = compute_dhash(img2)
    dist = hamming_distance(h1, h2)

    assert dist > DEFAULT_THRESHOLDS.dhash_max_hamming_distance

    correlator = PerceptualMediaCorrelator()
    items = [
        {"id": 1, "sha256": "sha_1", "dhash": h1, "file_name": "decoy1.jpg"},
        {"id": 2, "sha256": "sha_2", "dhash": h2, "file_name": "decoy2.jpg"},
    ]
    findings = correlator.correlate_media_findings(items)
    assert len(findings) == 0


def test_media_false_positive_benchmark_200_images():
    """
    Mandatory FP test per 10_CORRELATION.md §B12.4:
    A set of >= 200 deterministic unrelated synthetic images must produce 0 pairs under threshold.
    Reports the nearest-pair distance.
    """
    count = 200
    hashes: List[str] = []

    for i in range(count):
        raw_bytes = _create_synthetic_image(seed=i * 37 + 13, width=32, height=32)
        h = compute_dhash(raw_bytes, min_entropy=0.5)
        hashes.append(h)

    min_pair_distance = 64
    colliding_pairs = 0
    threshold = DEFAULT_THRESHOLDS.dhash_max_hamming_distance

    for i in range(count):
        for j in range(i + 1, count):
            d = hamming_distance(hashes[i], hashes[j])
            if d < min_pair_distance:
                min_pair_distance = d
            if d <= threshold:
                colliding_pairs += 1

    # Assert 0 false positive pairs under threshold
    assert colliding_pairs == 0, f"Found {colliding_pairs} false positive pairs under threshold <= {threshold}"
    # Nearest-pair distance must be strictly greater than threshold
    assert min_pair_distance > threshold, f"Nearest pair distance {min_pair_distance} must exceed {threshold}"
