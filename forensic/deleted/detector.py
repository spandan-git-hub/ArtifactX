"""Deleted message detection logic."""

from typing import List, Dict, Any, Optional
from datetime import datetime


class DeletedDetector:
    """Detects deleted messages in chat sequences."""

    def detect_deletions(
        self,
        messages: List[Any],
        source_app: str,
        evidence_id: int,
        case_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect deleted messages by analyzing sequence gaps in message timestamps.

        Args:
            messages: List of message objects (WhatsAppMessage or TelegramMessage)
            source_app: Either "whatsapp" or "telegram"
            evidence_id: ID of the evidence being analyzed
            case_id: ID of the case

        Returns:
            List of deleted message dictionaries ready to be saved to database
        """
        if not messages or len(messages) < 2:
            return []

        # Sort messages by timestamp
        sorted_messages = sorted(messages, key=lambda x: x.timestamp)

        deletions = []

        # Detect sequence gaps
        for i in range(len(sorted_messages) - 1):
            current_msg = sorted_messages[i]
            next_msg = sorted_messages[i + 1]

            # Calculate expected next ID based on platform
            expected_next_id = self._get_expected_next_id(current_msg, source_app)
            actual_next_id = self._get_message_id(next_msg, source_app)

            # If there's a gap in sequence numbers, we have deleted messages
            if expected_next_id is not None and actual_next_id is not None:
                if actual_next_id > expected_next_id:
                    gap_start = expected_next_id
                    gap_end = actual_next_id - 1
                    missing_count = gap_end - gap_start + 1

                    # Only consider it a deletion if there's a reasonable gap
                    # (avoid counting normal sequencing variations as deletions)
                    if missing_count > 0 and missing_count <= 100:  # Reasonable limit
                        confidence = self._calculate_confidence(
                            missing_count,
                            current_msg.timestamp,
                            next_msg.timestamp,
                            source_app
                        )

                        deletion_record = {
                            "case_id": case_id,
                            "evidence_id": evidence_id,
                            "source_app": source_app,
                            "chat_jid": self._get_chat_jid(current_msg, source_app),
                            "gap_start": gap_start,
                            "gap_end": gap_end,
                            "missing_count": missing_count,
                            "confidence_score": confidence,
                            "detection_method": "sequence_gap_analysis",
                            "detected_at": datetime.utcnow()
                        }
                        deletions.append(deletion_record)

        return deletions

    def _get_expected_next_id(self, message: Any, source_app: str) -> Optional[int]:
        """Get the expected next message ID in sequence."""
        if source_app == "whatsapp":
            # WhatsApp uses string message IDs, so we need to handle differently
            # For simplicity, we'll look at numeric parts if possible
            try:
                msg_id_str = message.message_id
                # Extract numeric part if it exists
                import re
                numbers = re.findall(r'\d+', msg_id_str)
                if numbers:
                    return int(numbers[-1]) + 1  # Last number + 1
            except (AttributeError, ValueError):
                pass
            return None
        elif source_app == "telegram":
            # Telegram uses integer message IDs
            try:
                return int(message.message_id) + 1
            except (AttributeError, ValueError):
                pass
            return None
        return None

    def _get_message_id(self, message: Any, source_app: str) -> Optional[int]:
        """Extract message ID as integer."""
        if source_app == "whatsapp":
            try:
                msg_id_str = message.message_id
                import re
                numbers = re.findall(r'\d+', msg_id_str)
                if numbers:
                    return int(numbers[-1])  # Last number
            except (AttributeError, ValueError):
                pass
            return None
        elif source_app == "telegram":
            try:
                return int(message.message_id)
            except (AttributeError, ValueError):
                pass
            return None
        return None

    def _get_chat_jid(self, message: Any, source_app: str) -> str:
        """Get chat identifier for grouping messages."""
        if source_app == "whatsapp":
            return getattr(message, 'key_remote_jid', getattr(message, 'sender_jid', 'unknown'))
        elif source_app == "telegram":
            return str(getattr(message, 'dialog_id', 'unknown'))
        return 'unknown'

    def _calculate_confidence(self, missing_count: int, timestamp1: int, timestamp2: int, source_app: str) -> float:
        """
        Calculate confidence score for deletion detection.

        Factors:
        - Size of gap (larger gaps = higher confidence, up to a point)
        - Time between messages (larger time gaps = lower confidence for same missing count)
        - Platform-specific factors
        """
        # Base confidence on missing count (normalized)
        # Assume gaps of 1-5 messages are suspicious, 6-10 are very likely deletions
        count_factor = min(missing_count / 10.0, 1.0)  # Max at 10 missing messages

        # Time factor - larger time gaps reduce confidence for same missing count
        time_diff = abs(timestamp2 - timestamp1)
        # Normalize time difference (assuming 1 day = 86400 seconds)
        time_factor = max(0.1, 1.0 - min(time_diff / (7 * 86400), 0.9))  # Min 0.1, decreases over a week

        # Platform factor (both platforms treated equally for now)
        platform_factor = 1.0

        # Combine factors
        confidence = (count_factor * 0.6 + time_factor * 0.3 + platform_factor * 0.1)
        return max(0.1, min(confidence, 0.95))  # Clamp between 0.1 and 0.95