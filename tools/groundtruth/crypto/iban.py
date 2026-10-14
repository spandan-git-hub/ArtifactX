"""IBAN generation and mod-97 validation for ground-truth datasets.

Follows master.md R6, R11, R20 and 02_GROUND_TRUTH_DATASETS.md §5:
- Implements ISO 7064 Mod 97-10 IBAN checksum validation.
- Generates valid fictitious IBANs from DeterministicRNG.
- Generates invalid-checksum decoys that differ slightly.
"""

from __future__ import annotations

import re
from typing import Tuple
from tools.groundtruth.rng import DeterministicRNG


def _char_to_digits(c: str) -> str:
    """Convert character to digits (A=10, B=11, ..., Z=35)."""
    if c.isdigit():
        return c
    return str(ord(c.upper()) - ord("A") + 10)


def validate_iban(iban: str) -> Tuple[bool, str]:
    """Validate an IBAN string using standard ISO 7064 mod-97 check.
    
    Returns (is_valid, normalized_or_error).
    """
    clean = re.sub(r"\s+", "", iban).upper()
    if len(clean) < 15 or len(clean) > 34:
        return False, f"Invalid IBAN length ({len(clean)})"

    if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]+", clean):
        return False, "Invalid IBAN characters or format"

    # Move first 4 characters to the end
    reordered = clean[4:] + clean[:4]

    # Convert letters to digits
    numeric_str = "".join(_char_to_digits(c) for c in reordered)

    # Modulo 97 check
    try:
        remainder = int(numeric_str) % 97
    except ValueError:
        return False, "Failed to parse numeric string"

    if remainder != 1:
        return False, f"Mod-97 checksum failed (remainder {remainder} != 1)"

    return True, clean


def generate_deterministic_iban(rng: DeterministicRNG, country_code: str = "DE") -> str:
    """Generate a valid fictitious IBAN with correct mod-97 check digits.
    
    Default Germany (DE): total 22 characters: DE + 2 check digits + 8 bank code + 10 account.
    """
    # 18 digits of fictitious bank + account data
    account_digits = "".join(str(rng.randint(0, 9)) for _ in range(18))

    # Calculate check digits: country + '00' moved to end
    temp_reordered = account_digits + country_code + "00"
    num_str = "".join(_char_to_digits(c) for c in temp_reordered)
    rem = int(num_str) % 97
    check = 98 - rem
    check_str = f"{check:02d}"

    iban = f"{country_code}{check_str}{account_digits}"
    is_val, _ = validate_iban(iban)
    assert is_val, f"Internal IBAN generator error for {iban}"
    return iban


def generate_iban_decoy(valid_iban: str) -> str:
    """Create an invalid-checksum decoy IBAN by modifying the check digits or last digit."""
    # Mutate the last digit
    clean = re.sub(r"\s+", "", valid_iban).upper()
    last_digit = int(clean[-1])
    new_last_digit = (last_digit + 1) % 10
    decoy = clean[:-1] + str(new_last_digit)
    is_val, _ = validate_iban(decoy)
    if is_val:
        # If it miraculously matched, try another modification
        decoy = clean[:-1] + str((last_digit + 5) % 10)
    return decoy
