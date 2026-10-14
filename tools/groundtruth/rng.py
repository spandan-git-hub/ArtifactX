"""Deterministic RNG wrapper for ground-truth data generation.

Follows master.md R11:
- Purely deterministic; same seed produces byte-identical results.
- NEVER uses time.time(), uuid.uuid4(), or os.urandom().
- All bytes, numbers, tokens, and identifiers derive strictly from random.Random(seed).
"""

import hashlib
import random
from typing import Sequence, TypeVar

T = TypeVar("T")


class DeterministicRNG:
    """Deterministic random number generator wrapper."""

    def __init__(self, seed: int | str):
        if isinstance(seed, str):
            # Derive 64-bit int from SHA-256 of seed string
            digest = hashlib.sha256(seed.encode("utf-8")).digest()
            seed_int = int.from_bytes(digest[:8], byteorder="big")
        else:
            seed_int = int(seed)
        self._seed = seed_int
        self._rng = random.Random(self._seed)

    @property
    def seed(self) -> int:
        return self._seed

    def randint(self, a: int, b: int) -> int:
        """Return random integer in [a, b]."""
        return self._rng.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        """Return random float in [a, b]."""
        return self._rng.uniform(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        """Return a random element from non-empty sequence seq."""
        return self._rng.choice(seq)

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        """Return a k length list of unique elements chosen from the population sequence."""
        return self._rng.sample(population, k)

    def shuffle(self, seq: list[T]) -> None:
        """Shuffle list in place deterministically."""
        self._rng.shuffle(seq)

    def random(self) -> float:
        """Return random float in [0.0, 1.0)."""
        return self._rng.random()

    def random_bytes(self, n: int) -> bytes:
        """Generate n pseudorandom bytes derived strictly from the seeded RNG."""
        # Use 32-bit random integers to build bytes
        out = bytearray()
        while len(out) < n:
            chunk = self._rng.getrandbits(32).to_bytes(4, byteorder="big")
            out.extend(chunk)
        return bytes(out[:n])

    def random_hex(self, n_bytes: int) -> str:
        """Generate hex string corresponding to n_bytes."""
        return self.random_bytes(n_bytes).hex()

    def whatsapp_key_id(self) -> str:
        """Generate a realistic WhatsApp message key ID.
        
        Typically starts with 3EB0 or similar prefix followed by 16-24 hex chars.
        Example: 3EB0A1B2C3D4E5F67890
        """
        suffix = self.random_bytes(10).hex().upper()
        return f"3EB0{suffix}"

    def unique_marker(self, prefix: str = "MARKER") -> str:
        """Generate a unique search token string for self-verification."""
        token = self.random_bytes(8).hex().upper()
        return f"__ARTIFACTX_{prefix}_{token}__"
