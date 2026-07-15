"""Forensic analysis engine for ArtifactX."""

from forensic.whatsapp.detector import is_whatsapp_database
from forensic.whatsapp.message_parser import extract_messages
from forensic.whatsapp.contact_parser import extract_contacts
from forensic.whatsapp.group_parser import extract_groups
from forensic.whatsapp.media_parser import extract_media_references

from forensic.telegram.detector import is_telegram_database
from forensic.telegram.message_parser import extract_messages as extract_tg_messages
from forensic.telegram.contact_parser import extract_contacts as extract_tg_contacts
from forensic.telegram.group_parser import extract_groups as extract_tg_groups
from forensic.telegram.media_parser import extract_media_references as extract_tg_media

from forensic.timeline.builder import TimelineBuilder
from forensic.timeline.normalizer import normalize_timestamp

from forensic.deleted.detector import DeletedDetector

from forensic.media.detector import detect_media_type
from forensic.media.metadata import extract_image_metadata, extract_media_metadata
from forensic.media.orphan import find_orphan_media_items, find_orphan_files, mark_media_orphan_status

from forensic.correlation.matcher import correlate_all
from forensic.correlation.graph import EvidenceGraph

__all__ = [
    # WhatsApp
    "is_whatsapp_database",
    "extract_messages",
    "extract_contacts",
    "extract_groups",
    "extract_media_references",
    # Telegram
    "is_telegram_database",
    "extract_tg_messages",
    "extract_tg_contacts",
    "extract_tg_groups",
    "extract_tg_media",
    # Timeline
    "TimelineBuilder",
    "normalize_timestamp",
    # Deleted
    "DeletedDetector",
    # Media
    "detect_media_type",
    "extract_image_metadata",
    "extract_media_metadata",
    "find_orphan_media_items",
    "find_orphan_files",
    "mark_media_orphan_status",
    # Correlation
    "correlate_all",
    "EvidenceGraph",
]