"""Perceptual Media Hashing and In-Memory Correlation Engine (B12.4).

Implements dHash (difference hash) and pHash (DCT-based perceptual hash)
with configurable Hamming distance thresholds, entropy validation, and zero disk writes.

Follows master.md R4, R8, R11, R12 and 10_CORRELATION.md §B12.4:
- All hash operations strictly in-memory from bytes (PIL.Image.open(BytesIO)).
- PIL.Image.MAX_IMAGE_PIXELS configured for untrusted-input hardening.
- Decompression bomb errors yield typed skip with explanatory note.
- Enforces minimum image dimension and Shannon entropy to eliminate blank/flat false positives.
- Confidence score strictly < 1.0 for all perceptual inferences.
"""

from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image

from forensic.correlation.models import CorrelationFinding, generate_deterministic_finding_id
from forensic.correlation.thresholds import CorrelationThresholds, DEFAULT_THRESHOLDS

# Hardened pixel ceiling for hostile evidence decompression (master.md R12)
Image.MAX_IMAGE_PIXELS = 100_000_000


class MediaHashError(Exception):
    """Base exception for media hashing errors."""
    pass


class DecompressionBombDetected(MediaHashError):
    """Raised when an image triggers Pillow's decompression bomb detection."""
    pass


class LowEntropyImageError(MediaHashError):
    """Raised when an image lacks sufficient visual information (blank/flat)."""
    pass


def compute_image_entropy(image_bytes: bytes) -> float:
    """Computes Shannon entropy of an image's pixel distribution in [0.0, 8.0]."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert to 8-bit grayscale
            gray = img.convert("L")
            hist = gray.histogram()
            total = sum(hist)
            if total == 0:
                return 0.0
            entropy = 0.0
            for count in hist:
                if count > 0:
                    p = count / total
                    entropy -= p * math.log2(p)
            return entropy
    except Exception:
        return 0.0


def compute_dhash(
    image_bytes: bytes,
    hash_size: int = 8,
    min_dimension: int = 16,
    min_entropy: float = 1.0,
) -> str:
    """
    Computes difference hash (dHash) for an in-memory image (zero disk writes).
    1. Validates dimensions and Shannon entropy.
    2. Resizes to (hash_size + 1, hash_size) -> (9x8) using Lanczos resampling.
    3. Compares adjacent horizontal pixel values.
    Returns 16-character hexadecimal string (64 bits).
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
            if w < min_dimension or h < min_dimension:
                raise LowEntropyImageError(f"Image dimensions {w}x{h} below minimum {min_dimension}x{min_dimension}")

            # Check entropy
            gray = img.convert("L")
            hist = gray.histogram()
            total = sum(hist)
            if total > 0:
                entropy = sum(-(c / total) * math.log2(c / total) for c in hist if c > 0)
                if entropy < min_entropy:
                    raise LowEntropyImageError(f"Image entropy {entropy:.2f} below minimum {min_entropy:.2f}")

            resample_filter = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
            resized = gray.resize((hash_size + 1, hash_size), resample_filter)
            pixels = list(resized.getdata())
            width = hash_size + 1

            bits = 0
            for y in range(hash_size):
                row_start = y * width
                for x in range(hash_size):
                    left = pixels[row_start + x]
                    right = pixels[row_start + x + 1]
                    bit = 1 if left > right else 0
                    bits = (bits << 1) | bit

            return f"{bits:016x}"
    except Image.DecompressionBombError as e:
        raise DecompressionBombDetected(f"Decompression bomb detected: {str(e)}") from e
    except LowEntropyImageError:
        raise
    except Exception as e:
        raise MediaHashError(f"Failed to compute dHash: {str(e)}") from e


def _compute_1d_dct(vector: List[float]) -> List[float]:
    """1D Discrete Cosine Transform (DCT-II)."""
    N = len(vector)
    result = []
    factor = math.pi / (2 * N)
    for k in range(N):
        s = sum(vector[n] * math.cos((2 * n + 1) * k * factor) for n in range(N))
        if k == 0:
            s *= math.sqrt(1.0 / N)
        else:
            s *= math.sqrt(2.0 / N)
        result.append(s)
    return result


def compute_phash(
    image_bytes: bytes,
    hash_size: int = 8,
    img_size: int = 32,
    min_dimension: int = 16,
    min_entropy: float = 1.0,
) -> str:
    """Computes perceptual hash (pHash) using 2D DCT."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
            if w < min_dimension or h < min_dimension:
                raise LowEntropyImageError(f"Image dimensions {w}x{h} below minimum")

            resample_filter = getattr(Image, "Resampling", Image).BILINEAR
            gray = img.convert("L").resize((img_size, img_size), resample_filter)
            raw_pixels = list(gray.getdata())
            matrix = [raw_pixels[i * img_size:(i + 1) * img_size] for i in range(img_size)]

            dct_rows = [_compute_1d_dct(row) for row in matrix]
            dct_cols = []
            for col_idx in range(img_size):
                col = [dct_rows[row_idx][col_idx] for row_idx in range(img_size)]
                dct_cols.append(_compute_1d_dct(col))

            dct_matrix = [[dct_cols[c][r] for c in range(hash_size)] for r in range(hash_size)]
            ac_coeffs = [
                dct_matrix[r][c]
                for r in range(hash_size)
                for c in range(hash_size)
                if not (r == 0 and c == 0)
            ]
            avg_val = sum(ac_coeffs) / len(ac_coeffs) if ac_coeffs else 0.0

            bits = 0
            for r in range(hash_size):
                for c in range(hash_size):
                    val = round(dct_matrix[r][c], 4)
                    bit = 1 if val > round(avg_val, 4) else 0
                    bits = (bits << 1) | bit

            return f"{bits:016x}"
    except Image.DecompressionBombError as e:
        raise DecompressionBombDetected(f"Decompression bomb detected: {str(e)}") from e
    except LowEntropyImageError:
        raise
    except Exception as e:
        raise MediaHashError(f"Failed to compute pHash: {str(e)}") from e


def hamming_distance(hash1_hex: str, hash2_hex: str) -> int:
    """Computes the bitwise Hamming distance between two 64-bit hexadecimal hash strings."""
    if not hash1_hex or not hash2_hex:
        return 64
    clean1 = hash1_hex.lower().replace("0x", "")
    clean2 = hash2_hex.lower().replace("0x", "")
    try:
        val1 = int(clean1, 16)
        val2 = int(clean2, 16)
        return bin(val1 ^ val2).count("1")
    except ValueError:
        return 64


class PerceptualMediaCorrelator:
    """Correlator linking visually identical, resized, or recompressed media exhibits."""

    def __init__(self, thresholds: CorrelationThresholds = DEFAULT_THRESHOLDS):
        self.thresholds = thresholds
        self.default_threshold = thresholds.dhash_max_hamming_distance
        self.version = thresholds.version

    def correlate_media_findings(
        self,
        media_records: List[Dict[str, Any]],
        threshold: Optional[int] = None,
    ) -> List[CorrelationFinding]:
        """
        Takes media items and returns CorrelationFinding instances.
        Each item is expected to have:
        'id', 'sha256', 'dhash', 'file_name', 'platform', 'evidence_id', 'timestamp'.
        """
        limit = threshold if threshold is not None else self.default_threshold
        findings: List[CorrelationFinding] = []
        n = len(media_records)

        for i in range(n):
            for j in range(i + 1, n):
                item_a = media_records[i]
                item_b = media_records[j]

                sha_a = (item_a.get("sha256") or "").lower()
                sha_b = (item_b.get("sha256") or "").lower()
                is_exact_sha = bool(sha_a and sha_b and sha_a == sha_b)

                dhash_a = item_a.get("dhash")
                dhash_b = item_b.get("dhash")
                dist = hamming_distance(dhash_a, dhash_b) if (dhash_a and dhash_b) else 64

                # Determine if matched
                if not is_exact_sha and dist > limit:
                    continue

                if is_exact_sha:
                    kind = "media_sha256"
                    strength = "strong"
                    match_cert = 1.0
                    conf = 0.95
                    norm_val = f"sha256_{sha_a}"
                    lim = ("Cryptographically identical SHA-256 media file.",)
                else:
                    kind = "media_dhash"
                    strength = "moderate" if dist > 0 else "strong"
                    # Monotonic function per 10_CORRELATION.md §B12.4
                    match_cert = round(max(0.0, 1.0 - (dist / 16.0)), 4)
                    conf = round(min(0.92, 0.85 * match_cert), 4)
                    norm_val = f"dhash_dist_{dist}_{dhash_a[:8]}_{dhash_b[:8]}"
                    lim = (
                        f"Perceptual dHash match with Hamming distance {dist} (threshold <= {limit}).",
                        "Visual similarity does not guarantee identical origin or content.",
                    )

                plat_a = item_a.get("platform") or "unknown"
                plat_b = item_b.get("platform") or "unknown"
                id_a = str(item_a.get("id") or item_a.get("file_name", "media_a"))
                id_b = str(item_b.get("id") or item_b.get("file_name", "media_b"))

                f_id = generate_deterministic_finding_id(
                    kind,
                    norm_val,
                    f"{plat_a}:{id_a}",
                    f"{plat_b}:{id_b}",
                    self.thresholds.version,
                )

                findings.append(CorrelationFinding(
                    finding_id=f_id,
                    kind=kind,
                    strength=strength,
                    match_certainty=match_cert,
                    confidence_score=conf,
                    normalized_value=norm_val,
                    left_ref={
                        "platform": plat_a,
                        "media_id": item_a.get("id"),
                        "file_name": item_a.get("file_name"),
                        "sha256": sha_a,
                        "dhash": dhash_a,
                        "evidence_id": item_a.get("evidence_id"),
                        "timestamp": item_a.get("timestamp"),
                    },
                    right_ref={
                        "platform": plat_b,
                        "media_id": item_b.get("id"),
                        "file_name": item_b.get("file_name"),
                        "sha256": sha_b,
                        "dhash": dhash_b,
                        "evidence_id": item_b.get("evidence_id"),
                        "timestamp": item_b.get("timestamp"),
                    },
                    limitations=lim,
                    provenance={
                        "algorithm": "dHash" if not is_exact_sha else "SHA256",
                        "hamming_distance": dist,
                        "threshold": limit,
                        "thresholds_version": self.thresholds.version,
                    },
                    thresholds_version=self.thresholds.version,
                    below_threshold=conf < self.thresholds.report_threshold_confidence,
                ))

        findings.sort(key=lambda f: f.sort_key())
        return findings

    def correlate_items(
        self,
        media_records: List[Dict[str, Any]],
        threshold: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Backwards compatibility adapter returning list of match dicts."""
        findings = self.correlate_media_findings(media_records, threshold)
        results = []
        for f in findings:
            results.append({
                "match_id": f.finding_id,
                "source_media_id": f.left_ref.get("media_id"),
                "target_media_id": f.right_ref.get("media_id"),
                "source_sha256": f.left_ref.get("sha256"),
                "target_sha256": f.right_ref.get("sha256"),
                "source_filename": f.left_ref.get("file_name"),
                "target_filename": f.right_ref.get("file_name"),
                "source_dhash": f.left_ref.get("dhash"),
                "target_dhash": f.right_ref.get("dhash"),
                "min_distance": f.provenance.get("hamming_distance", 0),
                "threshold": f.provenance.get("threshold", self.default_threshold),
                "confidence_score": f.confidence_score,
                "match_certainty": f.match_certainty,
                "classification": "PERCEPTUAL_MEDIA_MATCH",
                "limitations": list(f.limitations),
                "provenance": f.provenance,
            })
        return results
