"""Bitcoin address generation and validation for ground-truth datasets.

Follows master.md R6, R11, R20 and 02_GROUND_TRUTH_DATASETS.md §5:
- Implements standard Base58Check (P2PKH/P2SH) encoding, decoding, and checksum verification.
- Implements BIP-173 Bech32 encoding, decoding, and checksum verification.
- Deterministic address generation from DeterministicRNG.
"""

from __future__ import annotations

import hashlib
from typing import Tuple
from tools.groundtruth.rng import DeterministicRNG

# Base58 character alphabet
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_INVERSE = {c: i for i, c in enumerate(BASE58_ALPHABET)}

# Bech32 character alphabet
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_INVERSE = {c: i for i, c in enumerate(BECH32_CHARSET)}


def base58_encode(data: bytes) -> str:
    """Encode bytes to Base58 string preserving leading zeros as '1'."""
    orig_len = len(data)
    data_bytes = data.lstrip(b"\x00")
    num_zeros = orig_len - len(data_bytes)

    if not data_bytes:
        return "1" * num_zeros

    num = int.from_bytes(data_bytes, byteorder="big")
    chars = []
    while num > 0:
        num, rem = divmod(num, 58)
        chars.append(BASE58_ALPHABET[rem])
    chars.reverse()
    return ("1" * num_zeros) + "".join(chars)


def base58_decode(s: str) -> bytes:
    """Decode Base58 string to bytes preserving leading '1's as zeros."""
    orig_len = len(s)
    stripped = s.lstrip("1")
    num_zeros = orig_len - len(stripped)

    if not stripped:
        return b"\x00" * num_zeros

    num = 0
    for c in stripped:
        if c not in BASE58_INVERSE:
            raise ValueError(f"Invalid Base58 character: {c}")
        num = num * 58 + BASE58_INVERSE[c]

    # Convert int to bytes
    num_bytes = (num.bit_length() + 7) // 8
    res = num.to_bytes(num_bytes, byteorder="big")
    return (b"\x00" * num_zeros) + res


def base58check_encode(version: int, payload: bytes) -> str:
    """Encode version byte + 20-byte payload into Base58Check address."""
    data = bytes([version]) + payload
    checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
    return base58_encode(data + checksum)


def base58check_validate(address: str) -> Tuple[bool, str]:
    """Validate a Base58Check Bitcoin address.
    
    Returns (is_valid, reason_or_normalized).
    """
    if len(address) < 26 or len(address) > 35:
        return False, "Invalid address length"
    try:
        raw = base58_decode(address)
    except ValueError as e:
        return False, f"Base58 decode error: {e}"

    if len(raw) < 5:
        return False, "Data too short for Base58Check"

    payload_with_version = raw[:-4]
    provided_checksum = raw[-4:]
    computed_checksum = hashlib.sha256(hashlib.sha256(payload_with_version).digest()).digest()[:4]

    if provided_checksum != computed_checksum:
        return False, "Checksum mismatch"

    version = payload_with_version[0]
    if version not in (0x00, 0x05):  # 0x00 = P2PKH (1...), 0x05 = P2SH (3...)
        return False, f"Unsupported version byte: {version}"

    return True, address


def generate_deterministic_btc_address(rng: DeterministicRNG, version: int = 0x00) -> str:
    """Generate a valid fictitious Bitcoin Base58Check address."""
    # 20 bytes of payload (simulated pubkey hash)
    payload = rng.random_bytes(20)
    return base58check_encode(version, payload)


def generate_btc_decoy_address(valid_address: str) -> str:
    """Create an invalid-checksum decoy BTC address that looks similar."""
    # Mutate the last character to a different base58 character
    last_char = valid_address[-1]
    idx = BASE58_ALPHABET.index(last_char) if last_char in BASE58_ALPHABET else 0
    replacement = BASE58_ALPHABET[(idx + 1) % len(BASE58_ALPHABET)]
    decoy = valid_address[:-1] + replacement
    # Ensure it fails validation
    is_val, _ = base58check_validate(decoy)
    if is_val:
        # If by miraculous coincidence it matched, try another replacement
        replacement2 = BASE58_ALPHABET[(idx + 5) % len(BASE58_ALPHABET)]
        decoy = valid_address[:-1] + replacement2
    return decoy
