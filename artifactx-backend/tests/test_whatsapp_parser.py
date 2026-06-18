import unittest

from app.forensic.timeline_builder import build_timeline_events
from app.forensic.whatsapp_parser import parse_whatsapp_export


class WhatsAppParserTests(unittest.TestCase):
    def test_parses_messages_multiline_media_deleted_and_system_events(self):
        sample = "\n".join(
            [
                "12/06/2026, 9:15 PM - Alice: Hello",
                "continued line",
                "12/06/2026, 9:17 PM - Bob: <Media omitted>",
                "12/06/2026, 9:18 PM - Alice: This message was deleted",
                "12/06/2026, 9:19 PM - Messages and calls are end-to-end encrypted.",
            ]
        )

        result = parse_whatsapp_export(sample)

        self.assertEqual(result.statistics["message_count"], 4)
        self.assertEqual(result.statistics["participant_count"], 2)
        self.assertEqual(result.messages[0].content, "Hello\ncontinued line")
        self.assertEqual(result.messages[1].message_type, "media")
        self.assertEqual(result.messages[2].message_type, "deleted")
        self.assertEqual(result.messages[3].message_type, "system")

    def test_tracks_unattached_invalid_lines(self):
        result = parse_whatsapp_export("orphan line\n12/06/2026, 9:15 PM - Alice: Hello")

        self.assertEqual(result.statistics["skipped_count"], 1)
        self.assertEqual(result.skipped_rows, ["orphan line"])
        self.assertTrue(result.warnings)


class TimelineBuilderTests(unittest.TestCase):
    def test_builds_sorted_timeline_events(self):
        artifacts = [
            {
                "id": "2",
                "case_id": "case",
                "evidence_id": "evidence",
                "timestamp": None,
                "sender": "Bob",
                "content": "Later",
                "message_type": "message",
            },
            {
                "id": "1",
                "case_id": "case",
                "evidence_id": "evidence",
                "timestamp": parse_whatsapp_export("12/06/2026, 9:15 PM - Alice: Hello").messages[0].timestamp,
                "sender": "Alice",
                "content": "Hello",
                "message_type": "message",
            },
        ]

        events = build_timeline_events(artifacts)

        self.assertEqual(events[0]["artifact_id"], "1")
        self.assertEqual(events[0]["actor"], "Alice")
        self.assertEqual(events[1]["artifact_id"], "2")


if __name__ == "__main__":
    unittest.main()
