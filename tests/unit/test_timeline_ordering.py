"""Unit tests for timeline canonical event IDs, total ordering, and shuffle determinism (Rule R11, spec B11.2)."""

import random
import pytest
from forensic.timeline import (
    SourceRef,
    TimelineEvent,
    TimeValue,
    compute_canonical_event_id,
    compute_timeline_hash,
)


def test_canonical_event_id_deterministic():
    """Verify event_id is 32-hex and 100% deterministic across multiple calls with same inputs."""
    eid1 = compute_canonical_event_id(
        kind="message",
        evidence_sha256="aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
        source_table="message",
        row_or_offset=42,
        raw_time=1726000000000,
        key_facts={"chat_ref": "user1@s.whatsapp.net", "key_id": "3EB01234"},
    )
    eid2 = compute_canonical_event_id(
        kind="message",
        evidence_sha256="aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
        source_table="message",
        row_or_offset=42,
        raw_time=1726000000000,
        key_facts={"key_id": "3EB01234", "chat_ref": "user1@s.whatsapp.net"},  # different key insertion order
    )
    assert len(eid1) == 32
    assert eid1 == eid2


def test_sort_order_with_none_timestamps():
    """Verify events with utc_ms=None sort after events with timestamps deterministically."""
    sref = SourceRef(evidence_id=1, evidence_sha256="hash1", source_table="message", source_row_id=1)

    ev_with_time = TimelineEvent(
        event_id="ev_time_01",
        kind="message",
        app="whatsapp",
        time=TimeValue(raw=1726000000000, unit="ms", utc_ms=1726000000000, tz_basis="utc_source"),
        actor_ref="user1",
        chat_ref="chat1",
        summary="Message with time",
        source_refs=(sref,),
    )

    ev_no_time = TimelineEvent(
        event_id="ev_notime_02",
        kind="recovered_record",
        app="whatsapp",
        time=TimeValue(raw="", unit="unknown", utc_ms=None, tz_basis="not_applicable"),
        actor_ref="user2",
        chat_ref="chat1",
        summary="Partial record without time",
        source_refs=(sref,),
    )

    sorted_events = sorted([ev_no_time, ev_with_time], key=lambda e: e.sort_key())
    assert sorted_events[0].event_id == "ev_time_01"
    assert sorted_events[1].event_id == "ev_notime_02"


def test_tie_break_ordering():
    """Verify identical timestamps are tie-broken by kind priority, table, row, and event_id."""
    same_time = TimeValue(raw=1726000000000, unit="ms", utc_ms=1726000000000, tz_basis="utc_source")

    sref1 = SourceRef(evidence_id=1, evidence_sha256="hash1", source_table="message", source_row_id=10)
    sref2 = SourceRef(evidence_id=1, evidence_sha256="hash1", source_table="message_revoked", source_row_id=5)

    ev_msg = TimelineEvent(
        event_id="msg_01",
        kind="message",
        app="whatsapp",
        time=same_time,
        actor_ref="user1",
        chat_ref="chat1",
        summary="Normal message",
        source_refs=(sref1,),
    )

    ev_rev = TimelineEvent(
        event_id="rev_01",
        kind="revocation",
        app="whatsapp",
        time=same_time,
        actor_ref="user1",
        chat_ref="chat1",
        summary="Revocation",
        source_refs=(sref2,),
    )

    # message priority is 10, revocation is 30 -> message should sort before revocation
    sorted_evs = sorted([ev_rev, ev_msg], key=lambda e: e.sort_key())
    assert sorted_evs[0].kind == "message"
    assert sorted_evs[1].kind == "revocation"


def test_20x_shuffle_input_determinism():
    """
    R11 Determinism proof: shuffle input 20 times with seeded RNG.
    Assert resulting total sort order and timeline_hash are 100% identical on all 20 iterations.
    """
    rng = random.Random(42)

    # Build 50 diverse events
    events = []
    for i in range(50):
        # Some with identical timestamps to exercise tie-breaking
        ts_ms = 1726000000000 + (i % 15) * 1000
        # A few with None timestamps
        if i % 12 == 0:
            tv = TimeValue(raw="", unit="unknown", utc_ms=None, tz_basis="not_applicable")
        else:
            tv = TimeValue(raw=ts_ms, unit="ms", utc_ms=ts_ms, tz_basis="utc_source")

        kind = ["message", "location", "media_exif", "edit", "revocation"][i % 5]
        sref = SourceRef(
            evidence_id=1,
            evidence_sha256="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            source_table=f"table_{i % 3}",
            source_row_id=i,
        )
        eid = compute_canonical_event_id(
            kind=kind,
            evidence_sha256="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            source_table=f"table_{i % 3}",
            row_or_offset=i,
            raw_time=ts_ms,
            key_facts={"index": i},
        )
        ev = TimelineEvent(
            event_id=eid,
            kind=kind,
            app="whatsapp",
            time=tv,
            actor_ref=f"user_{i % 4}",
            chat_ref=f"chat_{i % 2}",
            summary=f"Event summary {i}",
            source_refs=(sref,),
            confidence_score=1.0,
            strength="deterministic",
        )
        events.append(ev)

    # Reference sort and hash
    ref_sorted = sorted(events, key=lambda e: e.sort_key())
    ref_hash = compute_timeline_hash(ref_sorted)
    ref_ids = [e.event_id for e in ref_sorted]

    # Run 20 shuffles
    for iteration in range(20):
        shuffled = list(events)
        rng.shuffle(shuffled)
        test_sorted = sorted(shuffled, key=lambda e: e.sort_key())
        test_hash = compute_timeline_hash(test_sorted)
        test_ids = [e.event_id for e in test_sorted]

        assert test_ids == ref_ids, f"Shuffle iteration {iteration} produced different ordering"
        assert test_hash == ref_hash, f"Shuffle iteration {iteration} produced different timeline_hash"
