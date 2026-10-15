"""Phone number normalization using phonenumbers (B12.2).

Follows master.md R8, R15, R20 and 10_CORRELATION.md §B12.2:
- NormalizedPhone outputs e164, region_assumed, valid, original.
- If region_assumed is True, finding receives limitation and lower match_certainty.
- Numbers that fail parsing stay unmatched (never fuzzy digit matching).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import re
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


@dataclass(frozen=True)
class NormalizedPhone:
    """Normalized E.164 phone representation with provenance and validity flags."""
    e164: Optional[str]
    region_assumed: bool
    valid: bool
    original: str
    country_code: Optional[int] = None
    national_number: Optional[int] = None


def normalize_phone(raw: str, default_region: str = "IN") -> NormalizedPhone:
    """
    Normalizes a phone number or WhatsApp JID to canonical E.164.

    Args:
        raw: Raw phone number string or JID (e.g. '+91 98765 43210', '098765-43210', '919876543210@s.whatsapp.net').
        default_region: ISO-3166-1 two-letter country code applied when raw number lacks international prefix.

    Returns:
        NormalizedPhone dataclass.
    """
    if not raw or not isinstance(raw, str):
        return NormalizedPhone(e164=None, region_assumed=False, valid=False, original=str(raw or ""))

    original = raw.strip()
    # Strip WhatsApp JID suffixes and device identifiers (e.g., :0@s.whatsapp.net, @s.whatsapp.net)
    cleaned = original
    if "@" in cleaned:
        cleaned = cleaned.split("@")[0]
    if ":" in cleaned:
        cleaned = cleaned.split(":")[0]
    cleaned = cleaned.strip()

    # Determine if international prefix '+' is present
    has_plus = cleaned.startswith("+")

    try:
        parsed = phonenumbers.parse(cleaned, default_region if not has_plus else None)
        is_valid = phonenumbers.is_valid_number(parsed)
        if not is_valid:
            # Check if possible number with loose validation
            is_possible = phonenumbers.is_possible_number(parsed)
            if not is_possible:
                return NormalizedPhone(
                    e164=None,
                    region_assumed=not has_plus,
                    valid=False,
                    original=original,
                    country_code=parsed.country_code,
                    national_number=parsed.national_number,
                )

        formatted_e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        return NormalizedPhone(
            e164=formatted_e164,
            region_assumed=not has_plus,
            valid=True,
            original=original,
            country_code=parsed.country_code,
            national_number=parsed.national_number,
        )
    except NumberParseException:
        # Fallback for bare digits when input doesn't start with 0 or + (e.g. WA JID like '919876543210')
        digits = re.sub(r"\D", "", cleaned)
        if digits and not has_plus:
            try:
                # Try prefixing with '+' directly
                parsed_plus = phonenumbers.parse("+" + digits, None)
                if phonenumbers.is_valid_number(parsed_plus):
                    return NormalizedPhone(
                        e164=phonenumbers.format_number(parsed_plus, PhoneNumberFormat.E164),
                        region_assumed=True,
                        valid=True,
                        original=original,
                        country_code=parsed_plus.country_code,
                        national_number=parsed_plus.national_number,
                    )
            except NumberParseException:
                pass

        return NormalizedPhone(
            e164=None,
            region_assumed=not has_plus,
            valid=False,
            original=original,
        )
