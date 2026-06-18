from datetime import datetime
from typing import Any


def build_timeline_events(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for artifact in artifacts:
        content = artifact.get("content") or ""
        summary = content.replace("\n", " ")
        if len(summary) > 180:
            summary = f"{summary[:177]}..."
        events.append(
            {
                "case_id": artifact["case_id"],
                "evidence_id": artifact["evidence_id"],
                "artifact_id": artifact["id"],
                "timestamp": artifact.get("timestamp"),
                "source": "whatsapp",
                "actor": artifact.get("sender"),
                "event_type": artifact.get("message_type", "message"),
                "summary": summary,
            }
        )
    return sorted(events, key=lambda event: event.get("timestamp") or datetime.max)
