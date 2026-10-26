"""Cross-Platform Handover Detection Engine (B12.5).

Detects platform handovers based on temporal proximity and explicit transition phrases.
Uses neutral forensic wording (PLATFORM_HANDOVER_CANDIDATE) to maintain objectivity.

Follows master.md R8, R10, R11 and 10_CORRELATION.md §B12.5:
- Uses normalized UTC timestamps (refuses events with unknown time).
- Strength is strictly <= moderate (users routinely use multiple apps concurrently).
- Confidence score is strictly < 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Tuple

from forensic.correlation.models import CorrelationFinding, generate_deterministic_finding_id
from forensic.correlation.thresholds import CorrelationThresholds, DEFAULT_THRESHOLDS

HANDOVER_PHRASES = [
    r"\b(switch|move|head|go|hop|shift)\s+(to|over\s+to|on)\s+(telegram|tg|whatsapp|wa|signal|wire|session|wickr)\b",
    r"\b(check|ping|hit|msg|message|text|dm|reach)\s+(me\s+on\s+|on\s+)?(telegram|tg|whatsapp|wa|signal)\b",
    r"\b(let'?s\s+talk|chat|continue|take\s+this)\s+(on|to|in)\s+(telegram|tg|whatsapp|wa|signal|secret)\b",
    r"\b(my\s+tg|my\s+telegram|my\s+wa|my\s+number)\s+is\b",
    r"\bt\.me\/[a-zA-Z0-9_]+\b",
    r"\bwa\.me\/[0-9]+\b",
]

COMPILED_HANDOVER_REGEXES = [re.compile(p, re.IGNORECASE) for p in HANDOVER_PHRASES]


@dataclass
class PlatformHandoverCandidate:
    """Represents a potential communication shift across platforms."""
    handover_id: str
    from_platform: str
    to_platform: str
    time_delta_seconds: int
    threshold_seconds: int
    from_message_id: str
    to_message_id: str
    from_timestamp: int
    to_timestamp: int
    from_sender: str
    to_sender: str
    from_body: str
    to_body: str
    transition_keywords: List[str] = field(default_factory=list)
    confidence_score: float = 0.85
    match_certainty: float = 0.80
    classification: str = "PLATFORM_HANDOVER_CANDIDATE"
    limitations: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handover_id": self.handover_id,
            "from_platform": self.from_platform,
            "to_platform": self.to_platform,
            "time_delta_seconds": self.time_delta_seconds,
            "threshold_seconds": self.threshold_seconds,
            "from_message_id": self.from_message_id,
            "to_message_id": self.to_message_id,
            "from_timestamp": self.from_timestamp,
            "to_timestamp": self.to_timestamp,
            "from_sender": self.from_sender,
            "to_sender": self.to_sender,
            "from_body": self.from_body,
            "to_body": self.to_body,
            "transition_keywords": self.transition_keywords,
            "confidence_score": round(self.confidence_score, 4),
            "match_certainty": round(self.match_certainty, 4),
            "classification": self.classification,
            "limitations": self.limitations,
            "provenance": self.provenance,
        }


class PlatformHandoverDetector:
    """Detector for cross-platform message sequence transitions."""

    def __init__(self, thresholds: CorrelationThresholds = DEFAULT_THRESHOLDS):
        self.thresholds = thresholds
        self.default_threshold_seconds = thresholds.handover_max_time_seconds
        self.version = thresholds.version

    def detect_keywords(self, text: str) -> List[str]:
        if not text:
            return []
        matches = []
        for regex in COMPILED_HANDOVER_REGEXES:
            found = regex.findall(text)
            if found:
                for item in found:
                    if isinstance(item, tuple):
                        matches.append(" ".join(str(x) for x in item if x))
                    else:
                        matches.append(str(item))
        return list(dict.fromkeys(matches))

    def detect_handovers(
        self,
        wa_messages: List[Any],
        tg_messages: List[Any],
        threshold_seconds: Optional[int] = None,
    ) -> List[PlatformHandoverCandidate]:
        """Detect temporal and keyword-based transition sequences between WA and TG."""
        threshold = threshold_seconds if threshold_seconds is not None else self.default_threshold_seconds
        candidates: List[PlatformHandoverCandidate] = []

        # Convert to standardized tuples: (platform, msg_id, sender, body, ts_sec, raw_msg)
        all_events = []
        for m in wa_messages:
            ts = getattr(m, "timestamp", None)
            if ts is None:
                ts = getattr(m, "ts_utc_ms", None) or getattr(m, "date_utc_ms", None)
            if ts is not None and ts > 0:
                ts_sec = ts // 1000 if ts > 10_000_000_000 else ts
                mid = getattr(m, "message_id", None) or getattr(m, "key_id", None) or getattr(m, "row_id", "")
                sender = getattr(m, "sender_jid", None) or getattr(m, "sender", "whatsapp_user")
                body = getattr(m, "body", None) or getattr(m, "text", "") or ""
                all_events.append(("whatsapp", str(mid), str(sender), body, ts_sec))

        for m in tg_messages:
            ts = getattr(m, "timestamp", None)
            if ts is None:
                ts = getattr(m, "date_utc_ms", None) or getattr(m, "ts_utc_ms", None)
            if ts is not None and ts > 0:
                ts_sec = ts // 1000 if ts > 10_000_000_000 else ts
                mid = getattr(m, "message_id", None) or getattr(m, "mid", None) or getattr(m, "row_id", "")
                sender = getattr(m, "sender_id", None) or getattr(m, "sender", "telegram_user")
                body = getattr(m, "body", None) or getattr(m, "text", "") or ""
                all_events.append(("telegram", str(mid), str(sender), body, ts_sec))

        # Sort chronologically
        all_events.sort(key=lambda x: x[4])

        for i in range(len(all_events) - 1):
            curr = all_events[i]
            nxt = all_events[i + 1]

            # Cross-platform only
            if curr[0] == nxt[0]:
                continue

            delta = nxt[4] - curr[4]
            if 0 <= delta <= threshold:
                keywords = self.detect_keywords(curr[3])
                has_keywords = len(keywords) > 0

                # Skip blank/empty message pairs without explicit handover keywords
                has_text = bool((curr[3] or "").strip() or (nxt[3] or "").strip())
                if not has_text and not has_keywords:
                    continue

                # Forensic confidence: elevated for explicit transition phrasing, moderate for continuous dialogue
                if has_keywords:
                    conf = 0.88
                    match_cert = 0.85
                    rationale = f"Explicit platform handover phrase ('{keywords[0]}') in {curr[0].title()} followed by message in {nxt[0].title()} within {delta}s."
                elif curr[2] == nxt[2] and curr[2] not in ("whatsapp_user", "telegram_user", "me", ""):
                    conf = 0.78
                    match_cert = 0.75
                    rationale = f"Same verified sender ({curr[2]}) transitioned from {curr[0].title()} to {nxt[0].title()} within {delta}s."
                else:
                    conf = 0.65
                    match_cert = 0.55
                    rationale = f"Cross-app temporal co-occurrence: {curr[0].title()} communication followed by {nxt[0].title()} activity within {delta}s."

                norm_val = f"{curr[0]}->{nxt[0]}_delta_{delta}s"
                h_id = generate_deterministic_finding_id(
                    "platform_handover",
                    norm_val,
                    f"{curr[0]}:{curr[1]}",
                    f"{nxt[0]}:{nxt[1]}",
                    self.thresholds.version,
                )

                candidates.append(PlatformHandoverCandidate(
                    handover_id=h_id,
                    from_platform=curr[0],
                    to_platform=nxt[0],
                    time_delta_seconds=delta,
                    threshold_seconds=threshold,
                    from_message_id=curr[1],
                    to_message_id=nxt[1],
                    from_timestamp=curr[4],
                    to_timestamp=nxt[4],
                    from_sender=curr[2],
                    to_sender=nxt[2],
                    from_body=curr[3][:120],
                    to_body=nxt[3][:120],
                    transition_keywords=keywords,
                    confidence_score=conf,
                    match_certainty=match_cert,
                    classification="PLATFORM_HANDOVER_CANDIDATE",
                    limitations=[
                        f"Temporal sequence gap: {delta}s (threshold <= {threshold}s).",
                        "Users routinely maintain concurrent sessions on multiple messaging platforms.",
                        "Transition keyword detection is heuristic." if has_keywords else "No explicit handover phrase found.",
                    ],
                    provenance={
                        "algorithm": "CrossPlatformHandover",
                        "time_delta_seconds": delta,
                        "threshold_seconds": threshold,
                        "transition_keywords": keywords,
                        "rationale": rationale,
                        "thresholds_version": self.thresholds.version,
                    },
                ))

        candidates.sort(key=lambda c: (c.time_delta_seconds, -c.confidence_score))
        return candidates

    def detect_handover_findings(
        self,
        wa_messages: List[Any],
        tg_messages: List[Any],
        threshold_seconds: Optional[int] = None,
    ) -> List[CorrelationFinding]:
        """Returns CorrelationFinding instances from handover candidates."""
        candidates = self.detect_handovers(wa_messages, tg_messages, threshold_seconds)
        findings = []

        for cand in candidates:
            norm_val = f"{cand.from_platform}->{cand.to_platform}_delta_{cand.time_delta_seconds}s"
            findings.append(CorrelationFinding(
                finding_id=cand.handover_id,
                kind="platform_handover",
                strength="moderate" if cand.transition_keywords else "weak_hint",
                match_certainty=cand.match_certainty,
                confidence_score=cand.confidence_score,
                normalized_value=norm_val,
                left_ref={
                    "platform": cand.from_platform,
                    "message_id": cand.from_message_id,
                    "timestamp": cand.from_timestamp,
                    "sender": cand.from_sender,
                    "body_snippet": cand.from_body,
                },
                right_ref={
                    "platform": cand.to_platform,
                    "message_id": cand.to_message_id,
                    "timestamp": cand.to_timestamp,
                    "sender": cand.to_sender,
                    "body_snippet": cand.to_body,
                },
                limitations=tuple(cand.limitations),
                provenance=cand.provenance,
                thresholds_version=self.thresholds.version,
                below_threshold=cand.confidence_score < self.thresholds.report_threshold_confidence,
            ))

        findings.sort(key=lambda f: f.sort_key())
        return findings
