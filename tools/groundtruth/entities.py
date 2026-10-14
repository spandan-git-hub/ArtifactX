"""Fictitious PII pools and entity generation for ground-truth datasets.

Follows master.md R6 and 02_GROUND_TRUTH_DATASETS.md:
- Fictitious PII only (names, +91 98765 4xxxx fake phone numbers, example.test URLs).
- Multilingual content (English, Hindi, Marathi, emoji).
- Fictitious geographic reference coordinates (WGS84).
"""

from dataclasses import dataclass
from typing import List
from tools.groundtruth.rng import DeterministicRNG


@dataclass(frozen=True)
class FictitiousPerson:
    full_name: str
    phone_number: str       # E.164 formatted: +91987654xxxx
    phone_digits: str       # Digits only: 91987654xxxx
    user_id: str            # 91987654xxxx
    server: str = "s.whatsapp.net"

    @property
    def jid(self) -> str:
        return f"{self.user_id}@{self.server}"


@dataclass(frozen=True)
class FictitiousGroup:
    subject: str
    group_id: str           # e.g. 1700000000-919876540001
    server: str = "g.us"

    @property
    def jid(self) -> str:
        return f"{self.group_id}@{self.server}"


@dataclass(frozen=True)
class FictitiousLocation:
    name: str
    address: str
    latitude: float
    longitude: float


# Device owner identity (fictitious)
PRIMARY_USER = FictitiousPerson(
    full_name="Aakash Nair (Investigator Test)",
    phone_number="+919876540000",
    phone_digits="919876540000",
    user_id="919876540000",
)

# Contacts pool (all fictitious, reserved/fake range 98765 4xxxx)
CONTACT_POOL = [
    FictitiousPerson(
        full_name="Rohan Sharma (Fictitious)",
        phone_number="+919876540001",
        phone_digits="919876540001",
        user_id="919876540001",
    ),
    FictitiousPerson(
        full_name="Priya Verma (Fictitious)",
        phone_number="+919876540002",
        phone_digits="919876540002",
        user_id="919876540002",
    ),
    FictitiousPerson(
        full_name="Vikram Patel (Fictitious)",
        phone_number="+919876540003",
        phone_digits="919876540003",
        user_id="919876540003",
    ),
    FictitiousPerson(
        full_name="Ananya Sen (Fictitious)",
        phone_number="+919876540004",
        phone_digits="919876540004",
        user_id="919876540004",
    ),
    # Additional person for empty chat scenario
    FictitiousPerson(
        full_name="Karan Malhotra (Fictitious Empty)",
        phone_number="+919876540005",
        phone_digits="919876540005",
        user_id="919876540005",
    ),
]

# Group definition (fictitious)
TEST_GROUP = FictitiousGroup(
    subject="Operation Garuda Discussion (Fictitious)",
    group_id="1725100000-919876540001",
)

# Sample fictitious locations
TEST_LOCATIONS = [
    FictitiousLocation(
        name="Gateway of India Reference Point",
        address="Apollo Bandar, Colaba, Mumbai, Maharashtra 400001",
        latitude=18.921984,
        longitude=72.834654,
    ),
    FictitiousLocation(
        name="Connaught Place Central Park",
        address="Connaught Place, New Delhi, Delhi 110001",
        latitude=28.632743,
        longitude=77.219597,
    ),
    FictitiousLocation(
        name="Tech Park Tower B",
        address="Whitefield Main Road, Bengaluru, Karnataka 560066",
        latitude=12.984521,
        longitude=77.731245,
    ),
]

# Message text corpus: professional, conversational, Hindi, Marathi, emoji, and technical
MESSAGE_TEXT_CORPUS: List[str] = [
    "Good morning. Did you review the quarterly log summary?",
    "Yes, I sent the updated figures earlier today.",
    "Please make sure the integrity hashes match before proceeding.",
    "All hashes have been confirmed against the primary ledger.",
    "Let's sync up around 3:00 PM for a quick check-in.",
    "Understood. I will prepare the presentation slides.",
    "Here is the reference document link: https://example.test/specs/archive-2026",
    "Received. Reading through section 3 right now.",
    "Can you share the location coordinates for the field visit?",
    "Sending the exact pin right away.",
    "Please check if the courier has delivered the test drive.",
    "Yes, package arrived safely at reception.",
    "The network backup completed successfully at 04:00.",
    "Thank you for the prompt update 👍",
    "Acknowledged. We are on track for the milestone release.",
    "Meeting rescheduled to 4:30 PM due to the team brief.",
    "Please verify the cryptographic keys before testing.",
    "Will do right after lunch.",
    "Can someone review PR #142 when available?",
    "Taking a look at it now.",
    # Hindi text (Unicode testing)
    "नमस्ते! क्या आप कल की समीक्षा बैठक के लिए उपलब्ध हैं?",
    "हाँ, मैंने सभी महत्वपूर्ण दस्तावेज़ तैयार कर लिए हैं।",
    "कृपया जाँच करें कि सभी डेटा बैकअप सुरक्षित हैं।",
    "सभी सिस्टम सामान्य रूप से चल रहे हैं। धन्यवाद!",
    "बैठक का समय दोपहर 2:00 बजे निर्धारित किया गया है।",
    "दस्तावेज़ की प्रतिलिपि यहाँ देखें: https://example.test/hi/doc-404",
    # Marathi text (Unicode testing)
    "नमस्कार! उद्याच्या बैठकीसाठी आवश्यक अहवाल तयार आहे का?",
    "होय, मी सर्व माहिती तपासून ठेवली आहे.",
    "प्रकल्पाचे काम वेळेत पूर्ण होईल अशी अपेक्षा आहे.",
    "कृपया नवीन अद्यतने लवकरात लवकर पाठवावीत.",
    # Mixed with emojis
    "Everything is confirmed for tomorrow's audit 📁🔍",
    "Great work team! Let's wrap up phase one 🚀✨",
    "Critical alert resolved: hash mismatch was a false positive 🔒✅",
    "Please send the revised draft as soon as possible 📝",
    "Standby, reviewing the attached photos now 📸",
]
