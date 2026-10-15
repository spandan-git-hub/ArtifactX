"""In-house Keccak-256 implementation for Ethereum EIP-55 checksum validation (B12.3, DEC-034).

Ethereum EIP-55 requires Keccak-256 (rate=1088 bits, capacity=512 bits, padding byte 0x01).
Note: Standard NIST SHA3-256 uses padding byte 0x06 and produces different output;
hashlib.sha3_256 MUST NOT be used for Ethereum checksums.
"""

from typing import List

# 24 Round Constants for Keccak-f[1600]
ROUND_CONSTANTS: List[int] = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]

# Rotation offsets for the 5x5 lanes
ROTATION_OFFSETS: List[List[int]] = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]


def _rotl64(x: int, n: int) -> int:
    return ((x << (n % 64)) & 0xFFFFFFFFFFFFFFFF) | (x >> ((64 - (n % 64)) % 64))


def _keccak_f1600(state: List[int]) -> None:
    """In-place Keccak-f[1600] permutation on 25 64-bit words."""
    for round_idx in range(24):
        # Theta step
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [_rotl64(c[(x + 1) % 5], 1) ^ c[(x + 4) % 5] for x in range(5)]
        for i in range(25):
            state[i] ^= d[i % 5]

        # Rho and Pi steps
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rotl64(state[x + 5 * y], ROTATION_OFFSETS[x][y])

        # Chi step
        for y in range(5):
            y5 = y * 5
            for x in range(5):
                state[x + y5] = b[x + y5] ^ ((~b[((x + 1) % 5) + y5]) & b[((x + 2) % 5) + y5])

        # Iota step
        state[0] ^= ROUND_CONSTANTS[round_idx]


def keccak_256(data: bytes) -> bytes:
    """
    Computes Ethereum-compatible Keccak-256 digest of input bytes.
    Rate = 1088 bits (136 bytes), Capacity = 512 bits, Suffix = 0x01.
    """
    rate = 136  # bytes
    state = [0] * 25

    # Pad data: Keccak domain padding with 0x01 suffix (pad10*1)
    pad_len = rate - (len(data) % rate)
    if pad_len == 1:
        padded = data + b"\x81"
    else:
        padded = data + b"\x01" + (b"\x00" * (pad_len - 2)) + b"\x80"

    # Absorb
    for block_start in range(0, len(padded), rate):
        block = padded[block_start:block_start + rate]
        for i in range(0, rate, 8):
            lane_idx = i // 8
            word = int.from_bytes(block[i:i + 8], byteorder="little")
            state[lane_idx] ^= word
        _keccak_f1600(state)

    # Squeeze 32 bytes (256 bits = 4 lanes of 8 bytes)
    out = bytearray()
    for i in range(4):
        out.extend(state[i].to_bytes(8, byteorder="little"))

    return bytes(out)
