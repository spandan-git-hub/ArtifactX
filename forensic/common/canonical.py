"""
Canonical JSON serialization for cryptographic hashing and audit integrity.
Complies with ArtifactX deterministic encoding rules (R11, spec B5.5):
- UTF-8 representation
- Keys sorted lexicographically
- Minimal separators (no whitespace: ',', ':')
- ensure_ascii=False
- Ints only, rejects non-integer floats to prevent float representation variance
"""

import json
from datetime import datetime, timezone
from typing import Any


def _canonical_default(obj: Any) -> Any:
    """Encoder default for standard non-JSON types."""
    if isinstance(obj, datetime):
        # Normalize to UTC ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        utc_dt = obj.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable in canonical form")


def _validate_no_floats(obj: Any) -> None:
    """Validate that data structure contains no non-integer floats per spec B5.5."""
    if isinstance(obj, float):
        if obj.is_integer():
            raise ValueError(
                f"Float value {obj!r} encountered in canonical data. "
                "Floats are forbidden in canonical audit hashing; convert to integer first."
            )
        raise ValueError(
            f"Float value {obj!r} encountered in canonical data. "
            "Floats are forbidden in canonical audit hashing per spec B5.5."
        )
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"Dictionary keys in canonical JSON must be strings, got {type(k).__name__}")
            _validate_no_floats(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _validate_no_floats(item)


def canonical_json(data: Any) -> str:
    """
    Serialize data to a deterministic, canonical JSON string.
    
    Rules:
    - Keys sorted
    - No whitespace separators (',', ':')
    - UTF-8 characters preserved (ensure_ascii=False)
    - Floats rejected (ints required)
    """
    _validate_no_floats(data)
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_canonical_default,
    )


def canonical_bytes(data: Any) -> bytes:
    """Return UTF-8 encoded bytes of canonical JSON representation."""
    return canonical_json(data).encode("utf-8")
