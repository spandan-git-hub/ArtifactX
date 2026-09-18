"""
Perceptual Media Hashing and Correlation Engine.
Implements dHash (difference hash) and pHash (DCT-based perceptual hash)
with configurable Hamming distance thresholds and deterministic scoring.
"""

from typing import List, Dict, Any, Optional, Tuple
import io
import math
import uuid
from PIL import Image


def compute_dhash(image_bytes: bytes, hash_size: int = 8) -> str:
    """
    Computes difference hash (dHash) for an image.
    1. Grayscale conversion.
    2. Resize to (hash_size + 1, hash_size) -> (9x8).
    3. Compare adjacent horizontal pixel values.
    Returns 16-character hexadecimal string (64 bits).
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("L").resize(
                (hash_size + 1, hash_size),
                Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
            )
            pixels = list(img.getdata())
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
    except Exception as e:
        raise ValueError(f"Failed to compute dHash: {str(e)}")


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


def compute_phash(image_bytes: bytes, hash_size: int = 8, img_size: int = 32) -> str:
    """
    Computes perceptual hash (pHash) using Discrete Cosine Transform (DCT).
    1. Grayscale conversion and resize to 32x32 using Bilinear resampling.
    2. Compute 2D DCT.
    3. Extract top-left 8x8 low-frequency coefficients (excluding DC term [0,0]).
    4. Compute mean of low-frequency AC coefficients.
    5. Set bit 1 if coefficient > mean, else 0.
    Returns 16-character hexadecimal string (64 bits).
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            resample_filter = getattr(Image, "Resampling", Image).BILINEAR
            img = img.convert("L").resize((img_size, img_size), resample_filter)
            raw_pixels = list(img.getdata())
            # Convert to 2D grid
            matrix = [raw_pixels[i * img_size:(i + 1) * img_size] for i in range(img_size)]

            # 2D DCT: apply 1D DCT on rows, then on columns
            dct_rows = [_compute_1d_dct(row) for row in matrix]
            dct_cols = []
            for col_idx in range(img_size):
                col = [dct_rows[row_idx][col_idx] for row_idx in range(img_size)]
                dct_cols.append(_compute_1d_dct(col))

            # Reconstruct (row, col) matrix from transposed column transform
            dct_matrix = [[dct_cols[c][r] for c in range(hash_size)] for r in range(hash_size)]

            # Extract AC low-frequency coefficients (excluding DC term [0,0])
            ac_coeffs = [
                dct_matrix[r][c]
                for r in range(hash_size)
                for c in range(hash_size)
                if not (r == 0 and c == 0)
            ]

            # Mean of AC coefficients
            avg_val = sum(ac_coeffs) / len(ac_coeffs) if ac_coeffs else 0.0

            # Generate 64 bits (stabilized with rounding to prevent float jitter near zero)
            bits = 0
            for r in range(hash_size):
                for c in range(hash_size):
                    val = round(dct_matrix[r][c], 4)
                    bit = 1 if val > round(avg_val, 4) else 0
                    bits = (bits << 1) | bit

            return f"{bits:016x}"
    except Exception as e:
        raise ValueError(f"Failed to compute pHash: {str(e)}")


def hamming_distance(hash1_hex: str, hash2_hex: str) -> int:
    """Computes the bitwise Hamming distance between two hexadecimal hash strings."""
    if not hash1_hex or not hash2_hex:
        return 64
    val1 = int(hash1_hex, 16)
    val2 = int(hash2_hex, 16)
    xor_val = val1 ^ val2
    # Popcount
    return bin(xor_val).count("1")


class PerceptualMediaCorrelator:
    """Correlator linking visually identical, resized, or recompressed media exhibits."""

    def __init__(self, default_threshold: int = 4):
        self.default_threshold = default_threshold
        self.version = "1.0.0"

    def correlate_items(
        self,
        media_records: List[Dict[str, Any]],
        threshold: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Takes list of media items with 'id', 'sha256', 'phash', 'dhash', 'file_name'.
        Returns pairwise matches within the Hamming distance threshold.
        """
        limit = threshold if threshold is not None else self.default_threshold
        matches = []
        n = len(media_records)

        for i in range(n):
            for j in range(i + 1, n):
                item_a = media_records[i]
                item_b = media_records[j]

                dhash_a = item_a.get("dhash")
                dhash_b = item_b.get("dhash")
                phash_a = item_a.get("phash")
                phash_b = item_b.get("phash")

                dist_dhash = hamming_distance(dhash_a, dhash_b) if (dhash_a and dhash_b) else 64
                dist_phash = hamming_distance(phash_a, phash_b) if (phash_a and phash_b) else 64

                # Min distance between available algorithms
                min_dist = min(dist_dhash, dist_phash)

                if min_dist <= limit:
                    # Confidence score inversely proportional to distance (0 dist = 1.0, 4 dist = 0.85)
                    confidence = max(0.70, 1.0 - (min_dist / 30.0))

                    matches.append({
                        "match_id": f"media_match_{uuid.uuid4().hex[:12]}",
                        "source_media_id": item_a.get("id"),
                        "target_media_id": item_b.get("id"),
                        "source_sha256": item_a.get("sha256"),
                        "target_sha256": item_b.get("sha256"),
                        "source_filename": item_a.get("file_name", ""),
                        "target_filename": item_b.get("file_name", ""),
                        "source_dhash": dhash_a,
                        "target_dhash": dhash_b,
                        "source_phash": phash_a,
                        "target_phash": phash_b,
                        "dhash_distance": dist_dhash,
                        "phash_distance": dist_phash,
                        "min_distance": min_dist,
                        "threshold": limit,
                        "confidence_score": round(confidence, 4),
                        "classification": "PERCEPTUAL_MEDIA_MATCH",
                        "limitations": [
                            f"Matched via perceptual hashing with Hamming distance {min_dist} (threshold <= {limit}).",
                            "Perceptual similarity indicates visual equivalence; distinct cryptographic SHA-256 remains."
                        ],
                        "provenance": {
                            "algorithms": ["dHash", "pHash"],
                            "version": self.version,
                            "threshold": limit,
                        }
                    })

        matches.sort(key=lambda m: (m["min_distance"], -m["confidence_score"]))
        return matches
