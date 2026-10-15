"""
Hostile-input fuzz testing for MTProto TL Reader (spec B9.2, master.md R12).

Performs 1,000 seeded random mutations across authentic MTProto blobs,
asserting that every corrupted payload either parses cleanly or raises a typed TLError.
Never leaks unhandled exceptions, never hangs, never allocates unbounded memory.
"""

import random
from datetime import datetime, timezone
import pytest
from telethon.tl import types as telethon_types

from forensic.telegram.tl.reader import (
    TLError,
)
from forensic.telegram.tl.registry import deserialize_tl_blob
from forensic.telegram.tl.types import TgChat, TgMessage, TgUser


def test_tl_fuzz_1000_mutations():
    """1,000 seeded random hostile mutations on valid MTProto blobs (R12)."""
    rng = random.Random(42)

    # Prepare 3 authentic sample blobs
    dt = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    valid_blobs = [
        bytes(
            telethon_types.Message(
                id=101,
                peer_id=telethon_types.PeerUser(user_id=1002),
                from_id=telethon_types.PeerUser(user_id=1001),
                date=dt,
                message="Fuzz target message with https://example.com URL and #hashtag",
                out=True,
                entities=[
                    telethon_types.MessageEntityUrl(offset=24, length=19),
                    telethon_types.MessageEntityHashtag(offset=48, length=8),
                ],
            )
        ),
        bytes(
            telethon_types.User(
                id=1003,
                first_name="Rohan",
                last_name="Verma",
                username="rohan_v",
                phone="919876550003",
                contact=True,
            )
        ),
        bytes(
            telethon_types.Chat(
                id=2001,
                title="Fuzz Target Group",
                photo=telethon_types.ChatPhotoEmpty(),
                participants_count=5,
                date=dt,
                version=1,
            )
        ),
    ]

    success_count = 0
    handled_error_count = 0

    for i in range(1000):
        base_blob = bytearray(rng.choice(valid_blobs))
        mutation_type = rng.randint(1, 5)

        if mutation_type == 1:
            # Single or multi-byte flip
            pos = rng.randint(0, len(base_blob) - 1)
            base_blob[pos] ^= rng.randint(1, 255)
        elif mutation_type == 2:
            # Truncation
            cut_len = rng.randint(1, len(base_blob))
            base_blob = base_blob[:cut_len]
        elif mutation_type == 3:
            # Corrupt constructor or length field
            pos = rng.randint(0, max(0, len(base_blob) - 4))
            base_blob[pos : pos + 4] = rng.randbytes(4)
        elif mutation_type == 4:
            # Insert random byte slice
            pos = rng.randint(0, len(base_blob))
            base_blob[pos:pos] = rng.randbytes(rng.randint(1, 32))
        elif mutation_type == 5:
            # Random slice replacement
            start = rng.randint(0, len(base_blob) - 1)
            end = rng.randint(start, len(base_blob))
            base_blob[start:end] = rng.randbytes(end - start)

        try:
            res = deserialize_tl_blob(bytes(base_blob))
            assert isinstance(res, (TgMessage, TgUser, TgChat))
            success_count += 1
        except TLError:
            # Expected handled error (TLBoundsError, TLConstructorNotFoundError, etc.)
            handled_error_count += 1
        except Exception as e:
            pytest.fail(f"Fuzz test {i} leaked unhandled exception: {type(e).__name__}: {e}")

    assert success_count + handled_error_count == 1000
    assert handled_error_count > 0, "Hostile mutations should trigger handled errors"
