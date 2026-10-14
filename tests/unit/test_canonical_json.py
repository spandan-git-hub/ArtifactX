"""Unit tests for canonical JSON serializer (forensic/common/canonical.py)."""

from datetime import datetime, timezone
import pytest
from forensic.common.canonical import canonical_json, canonical_bytes


def test_canonical_json_sorting_and_compactness():
    data = {"z": 1, "a": 2, "m": {"b": 3, "a": 4}}
    encoded = canonical_json(data)
    assert encoded == '{"a":2,"m":{"a":4,"b":3},"z":1}'
    assert " " not in encoded


def test_canonical_json_utf8_preservation():
    data = {"user": "राजेश", "city": "मुंबई", "emoji": "🔍"}
    encoded = canonical_json(data)
    assert "राजेश" in encoded
    assert "मुंबई" in encoded
    assert "🔍" in encoded
    raw = canonical_bytes(data)
    assert raw.decode("utf-8") == encoded


def test_canonical_json_datetime_normalization():
    dt_naive = datetime(2026, 10, 14, 12, 30, 45)
    dt_aware = datetime(2026, 10, 14, 12, 30, 45, tzinfo=timezone.utc)
    res_naive = canonical_json({"ts": dt_naive})
    res_aware = canonical_json({"ts": dt_aware})
    assert res_naive == '{"ts":"2026-10-14T12:30:45Z"}'
    assert res_aware == '{"ts":"2026-10-14T12:30:45Z"}'


def test_canonical_json_rejects_floats():
    with pytest.raises(ValueError, match="Floats are forbidden"):
        canonical_json({"val": 3.14})
    with pytest.raises(ValueError, match="Floats are forbidden"):
        canonical_json({"nested": [1, 2, 3.0]})


def test_canonical_json_nested_lists_and_ints():
    data = {"seq": 100, "items": [3, 1, 2], "flag": True, "none_val": None}
    assert canonical_json(data) == '{"flag":true,"items":[3,1,2],"none_val":null,"seq":100}'
