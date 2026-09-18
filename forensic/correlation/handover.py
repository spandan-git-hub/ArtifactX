"""
Cross-Platform Handover Detection Engine.
Detects platform handovers based on temporal proximity and explicit transition phrases.
Uses neutral forensic wording (PLATFORM_HANDOVER_CANDIDATE) to maintain judicial admissibility.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid
import re


HANDOVER_PHRASES = [
    r"\b(switch|move|head|go|hop|shift)\s+(to|over\s+to|on)\s+(telegram|tg|whatsapp|wa|signal|wire|session|wickr)\b",
    r"\b(check|ping|hit|msg|message|text|dm|reach)\s+(me\s+on\s+|on\s+)?(telegram|tg|whatsapp|wa|signal)\b",
    r"\b(let'?s\s+talk|chat|continue|take\s+this)\s+(on|to|in)\s+(telegram|tg|whatsapp|wa|signal|secret)\b",
    r"\b(my\s+tg|my\s+telegram|my\s+wa|my\s+number)\s+is\b",
    r"\bt\.me\/[a-zA-Z0-9_]+\b",
    r"\bwa\.me\/[0-9]+\b",
]

COMPILED_HANDOVER_REGEXES = [re.compile(pattern, re.IGNORECASE) for pattern in HANDOVER_PHRASES]


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
            "classification": self.classification,
            "limitations": self.limitations,
            "provenance": self.provenance,
        }


class PlatformHandoverDetector:
    """
    Detector for cross-platform message sequence transitions.
    Thresholds are fully configurable per run and recorded in output provenance.
    """

    def __init__(self, default_threshold_seconds: int = 180):
        self.default_threshold_seconds = default_threshold_seconds
        self.version = "1.0.0"

    def detect_keywords(self, text: str) -> List[str]:
        """Detect explicit transition phrases in a message body."""
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
        """
        Scan messages from WhatsApp and Telegram to identify sequence handovers.
        Checks both directions: WhatsApp -> Telegram and Telegram -> WhatsApp.
        """
        threshold = threshold_seconds if threshold_seconds is not None else self.default_threshold_seconds
        candidates: List[PlatformHandoverCandidate] = []

        # Normalize timestamps to seconds
        def get_ts_sec(msg) -> int:
            ts = getattr(msg, "timestamp", 0) or 0
            return ts // 1000 if ts > 10_000_000_000 else ts

        # 1. WhatsApp -> Telegram transitions
        for wa in wa_messages:
            wa_sec = get_ts_sec(wa)
            if not wa_sec:
                continue
            wa_body = getattr(wa, "body", "") or ""
            wa_kw = self.detect_keywords(wa_body)

            for tg in tg_messages:
                tg_sec = get_ts_sec(tg)
                if not tg_sec:
                    continue

                # Transition: WhatsApp message precedes Telegram message
                if 0 <= (tg_sec - wa_sec) <= threshold:
                    delta = tg_sec - wa_sec
                    tg_body = getattr(tg, "body", "") or ""
                    tg_kw = self.detect_keywords(tg_body)
                    all_kw = list(dict.fromkeys(wa_kw + tg_kw))

                    # Calculate confidence based on temporal proximity and explicit phrasing
                    base_confidence = max(0.65, 0.95 - (delta / threshold) * 0.30)
                    if all_kw:
                        base_confidence = min(0.99, base_confidence + 0.15)

                    candidate = PlatformHandoverCandidate(
                        handover_id=f"handover_{uuid.uuid4().hex[:12]}",
                        from_platform="whatsapp",
                        to_platform="telegram",
                        time_delta_seconds=delta,
                        threshold_seconds=threshold,
                        from_message_id=str(getattr(wa, "message_id", "")),
                        to_message_id=str(getattr(tg, "message_id", "")),
                        from_timestamp=wa_sec,
                        to_timestamp=tg_sec,
                        from_sender=str(getattr(wa, "sender_jid", "")),
                        to_sender=str(getattr(tg, "sender_id", "")),
                        from_body=wa_body,
                        to_body=tg_body,
                        transition_keywords=all_kw,
                        confidence_score=base_confidence,
                        classification="PLATFORM_HANDOVER_CANDIDATE",
                        limitations=[
                            f"Identified based on temporal delta ({delta}s <= {threshold}s).",
                            "Neutral candidate finding; does not infer motive, intent, or evasion."
                        ],
                        provenance={
                            "detector": "PlatformHandoverDetector",
                            "version": self.version,
                            "threshold_seconds": threshold,
                            "method": "TEMPORAL_AND_LEXICAL_CROSS_ANALYSIS",
                        },
                    )
                    candidates.append(candidate)

        # 2. Telegram -> WhatsApp transitions
        for tg in tg_messages:
            tg_sec = get_ts_sec(tg)
            if not tg_sec:
                continue
            tg_body = getattr(tg, "body", "") or ""
            tg_kw = self.detect_keywords(tg_body)

            for wa in wa_messages:
                wa_sec = get_ts_sec(wa)
                if not wa_sec:
                    continue

                if 0 <= (wa_sec - tg_sec) <= threshold:
                    delta = wa_sec - tg_sec
                    wa_body = getattr(wa, "body", "") or ""
                    wa_kw = self.detect_keywords(wa_body)
                    all_kw = list(dict.fromkeys(tg_kw + wa_kw))

                    base_confidence = max(0.65, 0.95 - (delta / threshold) * 0.30)
                    if all_kw:
                        base_confidence = min(0.99, base_confidence + 0.15)

                    candidate = PlatformHandoverCandidate(
                        handover_id=f"handover_{uuid.uuid4().hex[:12]}",
                        from_platform="telegram",
                        to_platform="whatsapp",
                        time_delta_seconds=delta,
                        threshold_seconds=threshold,
                        from_message_id=str(getattr(tg, "message_id", "")),
                        to_message_id=str(getattr(wa, "message_id", "")),
                        from_timestamp=tg_sec,
                        to_timestamp=wa_sec,
                        from_sender=str(getattr(tg, "sender_id", "")),
                        to_sender=str(getattr(wa, "sender_jid", "")),
                        from_body=tg_body,
                        to_body=wa_body,
                        transition_keywords=all_kw,
                        confidence_score=base_confidence,
                        classification="PLATFORM_HANDOVER_CANDIDATE",
                        limitations=[
                            f"Identified based on temporal delta ({delta}s <= {threshold}s).",
                            "Neutral candidate finding; does not infer motive, intent, or evasion."
                        ],
                        provenance={
                            "detector": "PlatformHandoverDetector",
                            "version": self.version,
                            "threshold_seconds": threshold,
                            "method": "TEMPORAL_AND_LEXICAL_CROSS_ANALYSIS",
                        },
                    )
                    candidates.append(candidate)

        # Sort by smallest time delta, then highest confidence
        candidates.sort(key=lambda c: (c.time_delta_seconds, -c.confidence_score))
        return candidates
