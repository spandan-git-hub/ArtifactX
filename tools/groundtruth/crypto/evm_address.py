"""Ethereum (EVM) EIP-55 mixed-case address generation and validation.

Follows master.md R6, R11, R20 and 02_GROUND_TRUTH_DATASETS.md §5:
- Uses Keccak-256 for EIP-55 checksum calculation (verified against official test vectors).
- Generates valid fictitious EVM addresses from DeterministicRNG.
- Generates invalid-checksum decoys that differ only in casing.
"""

from __future__ import annotations

import re
from typing import Tuple
from tools.groundtruth.rng import DeterministicRNG

# We use Cryptodome.Hash.keccak (pinned in dev environment)
try:
    from Cryptodome.Hash import keccak as _keccak

    def keccak256(data: bytes) -> bytes:
        k = _keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()

except ImportError:
    # Pure-Python fallback for keccak-256 if Cryptodome not present
    import hashlib
    # Note: hashlib.sha3_256 is NOT Keccak-256 (pad byte difference 0x01 vs 0x06).
    raise ImportError("Cryptodome.Hash.keccak required for accurate EIP-55 Keccak-256 calculation.")


def to_checksum_address(raw_hex_address: str) -> str:
    """Format a 40-hex character Ethereum address with EIP-55 checksum."""
    clean = raw_hex_address.lower()
    if clean.startswith("0x"):
        clean = clean[2:]
    if len(clean) != 40 or not re.fullmatch(r"[0-9a-f]{40}", clean):
        raise ValueError(f"Invalid Ethereum address hex length/content: {raw_hex_address}")

    hash_bytes = keccak256(clean.encode("ascii"))
    checksummed = []
    for i, ch in enumerate(clean):
        if ch in "0123456789":
            checksummed.append(ch)
        else:
            # Check the i-th nibble of hash
            hash_byte = hash_bytes[i // 2]
            nibble = (hash_byte >> 4) if (i % 2 == 0) else (hash_byte & 0x0F)
            if nibble >= 8:
                checksummed.append(ch.upper())
            else:
                checksummed.append(ch.lower())

    return "0x" + "".join(checksummed)


def validate_evm_address(address: str) -> Tuple[bool, str]:
    """Validate an EVM address against EIP-55 checksum specification.
    
    Returns (is_valid, normalized_or_error).
    """
    if not address.startswith("0x") and not address.startswith("0X"):
        return False, "Address must start with 0x"

    hex_part = address[2:]
    if len(hex_part) != 40 or not re.fullmatch(r"[0-9a-fA-F]{40}", hex_part):
        return False, "Invalid address length or characters"

    # If all-lower or all-upper, valid address format but no checksum
    if hex_part == hex_part.lower() or hex_part == hex_part.upper():
        return True, "0x" + hex_part.lower()

    # Mixed-case requires EIP-55 checksum match
    expected = to_checksum_address(hex_part)
    if address != expected:
        return False, f"EIP-55 checksum mismatch (expected {expected})"

    return True, expected


def generate_deterministic_evm_address(rng: DeterministicRNG) -> str:
    """Generate a valid fictitious EIP-55 checksummed EVM address."""
    # 20 bytes = 40 hex chars
    raw_bytes = rng.random_bytes(20)
    raw_hex = raw_bytes.hex()
    return to_checksum_address(raw_hex)


def generate_evm_decoy_address(valid_address: str) -> str:
    """Create an invalid-checksum decoy EVM address by flipping the casing of a letter."""
    # Find a letter char that can be flipped
    chars = list(valid_address)
    for i in range(2, len(chars)):
        c = chars[i]
        if c.isalpha():
            if c.isupper():
                chars[i] = c.lower()
            else:
                chars[i] = c.upper()
            break
    decoy = "".join(chars)
    is_val, _ = validate_evm_address(decoy)
    if is_val:
        # If it miraculously validated (e.g. became all lowercase), flip another letter
        for i in range(len(chars) - 1, 1, -1):
            if chars[i].isalpha():
                chars[i] = chars[i].lower() if chars[i].isupper() else chars[i].upper()
                break
        decoy = "".join(chars)
    return decoy
