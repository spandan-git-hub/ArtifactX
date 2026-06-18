from dataclasses import dataclass, field
from datetime import datetime
import re


ANDROID_PATTERNS = [
    re.compile(r"^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}), (?P<time>\d{1,2}:\d{2}(?::\d{2})?)\s?(?P<ampm>[AP]M|am|pm|AM|PM)? - (?P<body>.*)$"),
    re.compile(r"^\[(?P<date>\d{1,2}/\d{1,2}/\d{2,4}), (?P<time>\d{1,2}:\d{2}(?::\d{2})?)\s?(?P<ampm>[AP]M|am|pm|AM|PM)?\] (?P<body>.*)$"),
]
DATE_FORMATS = [
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%y %H:%M:%S",
    "%d/%m/%y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%y %H:%M:%S",
    "%m/%d/%y %H:%M",
    "%d/%m/%Y %I:%M:%S %p",
    "%d/%m/%Y %I:%M %p",
    "%d/%m/%y %I:%M:%S %p",
    "%d/%m/%y %I:%M %p",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%y %I:%M:%S %p",
    "%m/%d/%y %I:%M %p",
]


@dataclass
class ParsedMessage:
    timestamp: datetime | None
    sender: str | None
    content: str
    message_type: str
    raw_text: str
    flags: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    messages: list[ParsedMessage]
    skipped_rows: list[str]
    warnings: list[str]
    statistics: dict[str, int | list[str]]


def parse_whatsapp_export(text: str) -> ParseResult:
    messages: list[ParsedMessage] = []
    skipped_rows: list[str] = []
    warnings: list[str] = []
    current: ParsedMessage | None = None

    for line in text.splitlines():
        parsed = _parse_line(line)
        if parsed:
            if current:
                messages.append(current)
            current = parsed
            continue
        if current and line.strip():
            current.content = f"{current.content}\n{line}"
            current.raw_text = f"{current.raw_text}\n{line}"
        elif line.strip():
            skipped_rows.append(line)

    if current:
        messages.append(current)

    participants = sorted({message.sender for message in messages if message.sender})
    type_counts: dict[str, int] = {}
    for message in messages:
        type_counts[message.message_type] = type_counts.get(message.message_type, 0) + 1

    if skipped_rows:
        warnings.append(f"{len(skipped_rows)} line(s) could not be attached to a WhatsApp message.")

    return ParseResult(
        messages=messages,
        skipped_rows=skipped_rows,
        warnings=warnings,
        statistics={
            "message_count": len(messages),
            "skipped_count": len(skipped_rows),
            "participant_count": len(participants),
            "participants": participants,
            **{f"type_{key}_count": value for key, value in type_counts.items()},
        },
    )


def _parse_line(line: str) -> ParsedMessage | None:
    for pattern in ANDROID_PATTERNS:
        match = pattern.match(line)
        if not match:
            continue
        timestamp = _parse_timestamp(match.group("date"), match.group("time"), match.group("ampm"))
        body = match.group("body")
        sender, content = _split_sender(body)
        message_type, flags = _classify(content, sender)
        return ParsedMessage(
            timestamp=timestamp,
            sender=sender,
            content=content,
            message_type=message_type,
            raw_text=line,
            flags=flags,
        )
    return None


def _parse_timestamp(date_part: str, time_part: str, ampm: str | None) -> datetime | None:
    stamp = f"{date_part} {time_part}"
    if ampm:
        stamp = f"{stamp} {ampm.upper()}"
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(stamp, fmt)
        except ValueError:
            continue
    return None


def _split_sender(body: str) -> tuple[str | None, str]:
    if ": " not in body:
        return None, body.strip()
    sender, content = body.split(": ", 1)
    if len(sender) > 120:
        return None, body.strip()
    return sender.strip(), content.strip()


def _classify(content: str, sender: str | None) -> tuple[str, list[str]]:
    lowered = content.lower()
    flags: list[str] = []
    if sender is None:
        return "system", ["system_event"]
    if "omitted" in lowered or "<media omitted>" in lowered:
        return "media", ["media_placeholder"]
    if "deleted this message" in lowered or "message was deleted" in lowered:
        return "deleted", ["deleted_message"]
    if "missed voice call" in lowered or "missed video call" in lowered:
        flags.append("call_event")
    return "message", flags
