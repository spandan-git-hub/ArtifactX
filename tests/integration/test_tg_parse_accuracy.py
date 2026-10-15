"""
Integration tests: Telegram parse accuracy against ground-truth manifests (B9.7).
Verifies accuracy >= 99%, 100% on exact Telethon bytes, honest UNPARSED_BLOB classification,
and no-silent-drop invariants across dev and holdout datasets.
"""

import json
from pathlib import Path
import pytest

from forensic.telegram.parser import TelegramParser


def _load_dataset_bytes(dataset_dir: Path):
    db_bytes = (dataset_dir / "cache4.db").read_bytes()
    wal_path = dataset_dir / "cache4.db-wal"
    wal_bytes = wal_path.read_bytes() if wal_path.is_file() else None
    shm_path = dataset_dir / "cache4.db-shm"
    shm_bytes = shm_path.read_bytes() if shm_path.is_file() else None
    manifest_data = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    return db_bytes, wal_bytes, shm_bytes, manifest_data


@pytest.mark.parametrize("dataset_name", ["DS-05-dev", "DS-05-holdout", "DS-06-dev", "DS-06-holdout"])
def test_tg_parse_accuracy_manifest(dataset_name: str):
    """
    Verify parse accuracy vs ground-truth manifest >= 99% (B9.7).
    Compare (mid, dialog, sender, ts_utc_ms, text, media_kind, reply_to).
    """
    ds_dir = Path("testdata") / dataset_name
    if not ds_dir.is_dir():
        pytest.skip(f"Dataset {dataset_name} not found")

    db_bytes, wal_bytes, shm_bytes, manifest = _load_dataset_bytes(ds_dir)

    parser = TelegramParser(
        db_source=db_bytes,
        wal_source=wal_bytes,
        shm_source=shm_bytes,
        evidence_id=f"ev-{dataset_name}",
    )
    result = parser.parse()

    manifest_tg = manifest.get("telegram", {})
    manifest_messages = {m["mid"]: m for m in manifest_tg.get("messages", [])}
    parsed_messages = {m.mid: m for m in result.messages}
    unparsed_by_mid = {u.mid: u for u in result.unparsed_blobs if u.mid is not None}

    # Invariant: no silent drops
    assert len(result.messages) + len(unparsed_by_mid) >= len(manifest_messages)

    matches = 0
    misses = []
    exact_variant_matches = 0
    exact_variant_total = 0

    for mid, mm in manifest_messages.items():
        variant = mm.get("blob_variant", "exact")

        if variant in ("exact", "trailing_bytes"):
            if variant == "exact":
                exact_variant_total += 1

            if mid not in parsed_messages:
                misses.append(f"mid={mid} missing from parsed_messages (variant={variant})")
                continue

            pm = parsed_messages[mid]
            errs = []

            # 1. Dialog ID
            if pm.dialog_id != mm["uid"]:
                errs.append(f"dialog_id: {pm.dialog_id} != {mm['uid']}")

            # 2. Sender / From ID
            if pm.from_id != mm["from_id"]:
                errs.append(f"from_id: {pm.from_id} != {mm['from_id']}")

            # 3. UTC timestamp ms
            if pm.date_utc_ms != mm["date_utc_ms"]:
                errs.append(f"date_utc_ms: {pm.date_utc_ms} != {mm['date_utc_ms']}")

            # 4. Message text
            if pm.text != mm["text"]:
                errs.append(f"text mismatch: {pm.text!r} != {mm['text']!r}")

            # 5. Media kind
            expected_media = mm.get("media_type")
            if pm.media_kind != expected_media:
                errs.append(f"media_kind: {pm.media_kind} != {expected_media}")

            # 6. Reply to
            expected_reply = mm.get("reply_to_mid")
            if pm.reply_to_mid != expected_reply:
                errs.append(f"reply_to_mid: {pm.reply_to_mid} != {expected_reply}")

            if errs:
                misses.append(f"mid={mid} (variant={variant}) errors: {'; '.join(errs)}")
            else:
                matches += 1
                if variant == "exact":
                    exact_variant_matches += 1

        elif variant in ("unknown_constructor", "older_layer"):
            # Must be honestly classified as UNPARSED_BLOB (B9.3)
            if mid in unparsed_by_mid:
                matches += 1
            else:
                misses.append(f"mid={mid} expected UNPARSED_BLOB for variant={variant}, but got parsed message")

    total_msgs = len(manifest_messages)
    accuracy = matches / total_msgs if total_msgs > 0 else 0.0

    print(f"\n[{dataset_name}] Accuracy: {accuracy:.4f} ({matches}/{total_msgs}), Misses: {len(misses)}")
    if misses:
        print("Misses detail:\n" + "\n".join(misses[:10]))

    # Exit criteria asserts
    assert accuracy >= 0.99, f"Accuracy {accuracy:.4f} below 0.99 threshold. Misses: {misses}"
    assert exact_variant_matches == exact_variant_total, (
        f"Exact variant accuracy {exact_variant_matches}/{exact_variant_total} is not 100%"
    )


def test_tg_parse_documented_blob_variants_dev():
    """Verify specific behavior of mid 50, mid 80, mid 120 documented blob variants (B9.2, B9.3)."""
    ds_dir = Path("testdata/DS-05-dev")
    db_bytes, wal_bytes, shm_bytes, manifest = _load_dataset_bytes(ds_dir)

    parser = TelegramParser(db_source=db_bytes, wal_source=wal_bytes, shm_source=shm_bytes, evidence_id="ev-dev")
    result = parser.parse()

    parsed_messages = {m.mid: m for m in result.messages}
    unparsed_by_mid = {u.mid: u for u in result.unparsed_blobs if u.mid is not None}

    # mid 50: trailing_bytes (must parse + flag trailing bookkeeping bytes)
    assert 50 in parsed_messages
    m50 = parsed_messages[50]
    assert m50.trailing_bytes_info is not None
    assert m50.trailing_bytes_info["length"] == 8
    assert m50.trailing_bytes_info["prefix_hex"] == "00000001aabbccdd"
    assert any("trailing" in lim.lower() for lim in m50.limitations)

    # mid 80: unknown_constructor 0xDEADBEEF (must be UNPARSED_BLOB with constructor hex)
    assert 80 in unparsed_by_mid
    u80 = unparsed_by_mid[80]
    assert u80.constructor_id_hex == "0xdeadbeef"
    assert "0xdeadbeef" in u80.reason.lower()
    assert u80.container_metadata["source"] == "from_column"

    # mid 120: older_layer 0x38114EE2 (must be UNPARSED_BLOB with constructor hex)
    assert 120 in unparsed_by_mid
    u120 = unparsed_by_mid[120]
    assert u120.constructor_id_hex == "0x38114ee2"
    assert "0x38114ee2" in u120.reason.lower()
    assert u120.container_metadata["source"] == "from_column"


def test_tg_parse_multi_views_and_dialog_resolution():
    """Verify multi-view exposure (main_view and post_wal_view) and dialog peer resolution."""
    ds_dir = Path("testdata/DS-05-dev")
    db_bytes, wal_bytes, shm_bytes, manifest = _load_dataset_bytes(ds_dir)

    parser = TelegramParser(db_source=db_bytes, wal_source=wal_bytes, shm_source=shm_bytes, evidence_id="ev-views")
    result = parser.parse()

    # Both views exposed
    assert "main_view" in result.views_parsed
    assert "post_wal_view" in result.views_parsed

    # Live messages carry post_wal_view provenance
    for msg in result.messages:
        assert msg.view == "post_wal_view"
        assert msg.provenance.method == "cache4_post_wal_view"

    # Dialogs peer kind mapping
    dialog_map = {d.dialog_id: d for d in result.dialogs}
    assert 1002 in dialog_map
    assert dialog_map[1002].peer_kind == "user"
    assert dialog_map[1002].peer_id == 1002

    assert -2001 in dialog_map
    assert dialog_map[-2001].peer_kind == "chat"
    assert dialog_map[-2001].peer_id == 2001
    assert dialog_map[-2001].title == "ArtifactX TG Taskforce"


def test_tg_parse_determinism():
    """Verify determinism: parsing same input twice yields identical results and finding IDs (R11)."""
    ds_dir = Path("testdata/DS-05-dev")
    db_bytes, wal_bytes, shm_bytes, manifest = _load_dataset_bytes(ds_dir)

    p1 = TelegramParser(db_source=db_bytes, wal_source=wal_bytes, shm_source=shm_bytes, evidence_id="ev-det")
    r1 = p1.parse()

    p2 = TelegramParser(db_source=db_bytes, wal_source=wal_bytes, shm_source=shm_bytes, evidence_id="ev-det")
    r2 = p2.parse()

    assert len(r1.messages) == len(r2.messages)
    assert len(r1.unparsed_blobs) == len(r2.unparsed_blobs)
    for m1, m2 in zip(r1.messages, r2.messages):
        assert m1.finding_id == m2.finding_id
        assert m1.text == m2.text
        assert m1.date_utc_ms == m2.date_utc_ms
