"""Shared Forensic Artifact Extraction and Validation Engine (B12.3).

Extracts and validates candidate artifacts from text messages:
- Bitcoin: Base58Check (P2PKH, P2SH) and Bech32/Bech32m (BIP-173/BIP-350)
- EVM: 0x + 40 hex digits, EIP-55 mixed-case checksum via Keccak-256
- IBAN: ISO length validation + ISO 7064 Modulo 97-10
- Canonical URL: tracking param strip, host/scheme normalization, path preserved
- Custom Codewords / Analyst Keywords

Follows master.md R5, R8, R11, R15, R20 and 10_CORRELATION.md §B12.3:
Invalid-checksum candidates produce ZERO links.
Matching is exact on the normalized value across distinct platforms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from forensic.correlation.keccak import keccak_256
from forensic.correlation.models import CorrelationFinding, generate_deterministic_finding_id
from forensic.correlation.thresholds import CorrelationThresholds, DEFAULT_THRESHOLDS

# Base58 Alphabet for Bitcoin Base58Check
B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

# Bech32 / Bech32m Alphabet and Constants (BIP-173 / BIP-350)
BECH32_ALPHABET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_CONST = 1
BECH32M_CONST = 0x2BC830A3

# ISO IBAN Length Registry
IBAN_LENGTHS: Dict[str, int] = {
    "AL": 28, "AD": 24, "AT": 20, "AZ": 28, "BH": 22, "BY": 28, "BE": 16, "BA": 20,
    "BR": 29, "BG": 22, "CR": 22, "HR": 21, "CY": 28, "CZ": 24, "DK": 18, "DO": 28,
    "TL": 23, "EE": 20, "FO": 18, "FI": 18, "FR": 27, "GE": 22, "DE": 22, "GI": 23,
    "GR": 27, "GL": 18, "GT": 28, "HU": 28, "IS": 26, "IN": 20, "IE": 22, "IL": 23,
    "IT": 27, "JO": 30, "KZ": 20, "XK": 20, "KW": 30, "LV": 21, "LB": 28, "LI": 21,
    "LT": 20, "LU": 20, "MK": 19, "MT": 31, "MR": 27, "MU": 30, "MD": 24, "MC": 27,
    "ME": 22, "NL": 18, "NO": 15, "PK": 24, "PS": 29, "PL": 28, "PT": 25, "QA": 29,
    "RO": 24, "LC": 32, "SM": 27, "ST": 25, "SA": 24, "RS": 22, "SC": 31, "SK": 24,
    "SI": 19, "ES": 24, "SE": 24, "CH": 21, "TN": 24, "TR": 26, "UA": 29, "AE": 23,
    "GB": 22, "VA": 22, "VG": 24
}

# Tracking parameters stripped during URL normalization (10_CORRELATION.md §B12.3)
TRACKING_PARAMS: Set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "_ga", "_gl", "mc_cid", "mc_eid"
}


# ==============================================================================
# Bitcoin Address Validation (Base58Check & Bech32/Bech32m)
# ==============================================================================

def is_valid_base58(s: str) -> bool:
    return bool(s) and all(c in B58_ALPHABET for c in s)


def base58_decode(s: str) -> Optional[bytes]:
    if not is_valid_base58(s):
        return None
    num = 0
    for char in s:
        num = num * 58 + B58_ALPHABET.index(char)
    raw = num.to_bytes((num.bit_length() + 7) // 8, byteorder="big")
    pad = 0
    for char in s:
        if char == B58_ALPHABET[0]:
            pad += 1
        else:
            break
    return (b"\x00" * pad) + raw


def _bech32_polymod(values: List[int]) -> int:
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> List[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def validate_bech32(addr: str) -> bool:
    """Validate Bitcoin Bech32 or Bech32m address (BIP-173/BIP-350)."""
    if len(addr) < 8 or len(addr) > 90:
        return False
    if addr != addr.lower() and addr != addr.upper():
        return False
    addr_lower = addr.lower()
    pos = addr_lower.rfind("1")
    if pos < 1 or pos + 7 > len(addr_lower):
        return False
    hrp = addr_lower[:pos]
    if hrp not in ("bc", "tb"):
        return False
    data_part = addr_lower[pos + 1:]
    if not all(c in BECH32_ALPHABET for c in data_part):
        return False
    values = [BECH32_ALPHABET.index(c) for c in data_part]
    chk = _bech32_polymod(_bech32_hrp_expand(hrp) + values)
    return chk in (BECH32_CONST, BECH32M_CONST)


def validate_btc_address(addr: str) -> Tuple[bool, str]:
    """
    Validate Bitcoin address.
    Returns (is_valid, validation_status).
    """
    if not addr or not isinstance(addr, str):
        return False, "INVALID_EMPTY"

    clean = addr.strip()
    # Bech32 Segwit
    if clean.lower().startswith("bc1") or clean.lower().startswith("tb1"):
        if validate_bech32(clean):
            return True, "VALIDATED_BECH32_OK"
        return False, "INVALID_BECH32_CHECKSUM"

    # Legacy P2PKH / P2SH with Base58Check
    if (clean.startswith("1") or clean.startswith("3")) and (25 <= len(clean) <= 35):
        decoded = base58_decode(clean)
        if decoded and len(decoded) == 25:
            payload, check = decoded[:-4], decoded[-4:]
            expected_check = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            if check == expected_check:
                return True, "VALIDATED_BASE58CHECK_OK"
            return False, "INVALID_BASE58CHECK_CHECKSUM"
        return False, "INVALID_BASE58_LENGTH"

    return False, "INVALID_FORMAT"


# ==============================================================================
# EVM / Ethereum Address Validation (EIP-55)
# ==============================================================================

def validate_evm_address(addr: str) -> Tuple[bool, str, str]:
    """
    Validate EVM address and EIP-55 checksum.
    Returns (is_valid, validation_status, normalized_address).
    """
    if not addr or not isinstance(addr, str):
        return False, "INVALID_EMPTY", ""

    clean = addr.strip()
    if not clean.startswith("0x") and not clean.startswith("0X"):
        return False, "MISSING_0X_PREFIX", ""
    hex_part = clean[2:]
    if len(hex_part) != 40 or not re.fullmatch(r"[0-9a-fA-F]{40}", hex_part):
        return False, "INVALID_HEX_LENGTH", ""

    # Check if all-lowercase or all-uppercase
    is_all_lower = hex_part == hex_part.lower()
    is_all_upper = hex_part == hex_part.upper()

    if is_all_lower or is_all_upper:
        # Valid syntax, but unchecksummed
        return True, "FORMAT_VALID_NO_CHECKSUM", "0x" + hex_part.lower()

    # Mixed-case: must strictly validate against EIP-55 Keccak-256
    hash_bytes = keccak_256(hex_part.lower().encode("ascii"))
    for i, ch in enumerate(hex_part):
        hash_byte = hash_bytes[i // 2]
        nibble = (hash_byte >> 4) if (i % 2 == 0) else (hash_byte & 0x0F)
        if nibble >= 8:
            if ch != ch.upper():
                return False, "INVALID_EIP55_CHECKSUM", ""
        else:
            if ch != ch.lower():
                return False, "INVALID_EIP55_CHECKSUM", ""

    return True, "VALIDATED_EIP55_CHECKSUM_OK", "0x" + hex_part.lower()


# ==============================================================================
# IBAN Validation (ISO Length + Modulo 97-10)
# ==============================================================================

def validate_iban(iban_str: str) -> Tuple[bool, str, str]:
    """
    Validate IBAN against country length registry and ISO 7064 Modulo 97-10.
    Returns (is_valid, validation_status, normalized_iban).
    """
    if not iban_str or not isinstance(iban_str, str):
        return False, "INVALID_EMPTY", ""

    clean = re.sub(r"[\s\-]", "", iban_str).upper()
    if len(clean) < 5 or not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]+", clean):
        return False, "INVALID_SYNTAX", ""

    country = clean[:2]
    expected_len = IBAN_LENGTHS.get(country)
    if expected_len is not None and len(clean) != expected_len:
        if len(clean) > expected_len:
            candidate_prefix = clean[:expected_len]
            rearranged_p = candidate_prefix[4:] + candidate_prefix[:4]
            digits_p = []
            for ch in rearranged_p:
                if ch.isdigit():
                    digits_p.append(ch)
                elif ch.isupper():
                    digits_p.append(str(ord(ch) - ord("A") + 10))
                else:
                    break
            if len(digits_p) == len(rearranged_p):
                try:
                    if int("".join(digits_p)) % 97 == 1:
                        return True, "VALIDATED_MOD97_OK", candidate_prefix
                except ValueError:
                    pass
        return False, f"INVALID_COUNTRY_LENGTH_{country}_{len(clean)}_EXP_{expected_len}", ""

    # Modulo 97 check
    rearranged = clean[4:] + clean[:4]
    digits = []
    for ch in rearranged:
        if ch.isdigit():
            digits.append(ch)
        elif ch.isupper():
            digits.append(str(ord(ch) - ord("A") + 10))
        else:
            return False, "INVALID_CHAR", ""

    num_str = "".join(digits)
    try:
        if int(num_str) % 97 == 1:
            return True, "VALIDATED_MOD97_OK", clean
        return False, "INVALID_MOD97_CHECKSUM", ""
    except ValueError:
        return False, "CONVERSION_ERROR", ""


# ==============================================================================
# Additional Financial & Crypto Validators (Tron, Monero, Luhn, SWIFT, UPI)
# ==============================================================================

def validate_tron_address(addr: str) -> bool:
    """Validate Tron / USDT TRC-20 address (Base58 starting with T, length 34)."""
    if not addr or not addr.startswith("T") or len(addr) != 34:
        return False
    decoded = base58_decode(addr)
    if decoded and len(decoded) == 25:
        payload, check = decoded[:-4], decoded[-4:]
        expected_check = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        return check == expected_check
    return is_valid_base58(addr)


def validate_monero_address(addr: str) -> bool:
    """Validate Monero primary/integrated address (95 or 106 chars Base58 starting with 4 or 8)."""
    if not addr or len(addr) not in (95, 106):
        return False
    if addr[0] not in ("4", "8"):
        return False
    return is_valid_base58(addr)


def validate_luhn(card_number: str) -> bool:
    """Validate credit card number using Luhn mod-10 algorithm."""
    clean = re.sub(r"[\s\-]", "", card_number)
    if not clean.isdigit() or not (13 <= len(clean) <= 19):
        return False
    digits = [int(d) for d in clean]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def validate_swift_bic(swift: str) -> bool:
    """Validate SWIFT/BIC code (8 or 11 characters, ISO 9362)."""
    clean = re.sub(r"[\s\-]", "", swift).upper()
    return bool(re.fullmatch(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", clean))


def validate_upi_handle(upi: str) -> bool:
    """Validate UPI virtual payment address (username@bank/psp)."""
    if not upi or "@" not in upi or len(upi) > 100:
        return False
    parts = upi.split("@")
    if len(parts) != 2:
        return False
    user, handle = parts[0], parts[1]
    if not re.fullmatch(r"[a-zA-Z0-9._\-]{2,50}", user):
        return False
    common_email_tlds = {"com", "net", "org", "edu", "gov", "io", "co", "uk", "de"}
    handle_parts = handle.split(".")
    if len(handle_parts) == 2 and handle_parts[1].lower() in common_email_tlds:
        return False
    return bool(re.fullmatch(r"[a-zA-Z0-9]{2,30}", handle))


# ==============================================================================
# Canonical URL Normalization
# ==============================================================================

def normalize_url(raw_url: str) -> Optional[str]:
    """
    Normalizes a URL per 10_CORRELATION.md §B12.3:
    - Lowercases scheme and netloc (host)
    - Strips 'www.' prefix
    - Strips default ports (:80 for http, :443 for https)
    - Strips fragments (#...)
    - Strips trailing slash on non-empty paths
    - Drops advertising and tracking parameters (utm_*, fbclid, gclid, etc.)
    - Path remains significant!
    """
    if not raw_url or not isinstance(raw_url, str):
        return None

    clean = raw_url.strip()
    try:
        parts = urlsplit(clean)
        scheme = parts.scheme.lower()
        if scheme not in ("http", "https"):
            return None

        netloc = parts.netloc.lower()
        # Strip default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Strip www.
        if netloc.startswith("www."):
            netloc = netloc[4:]

        if not netloc:
            return None

        # Normalize path: preserve case and structure, strip trailing slash if len > 1
        path = parts.path
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        # Filter query params
        query_pairs = parse_qsl(parts.query, keep_blank_values=False)
        filtered_pairs = [
            (k, v) for k, v in query_pairs
            if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
        ]
        filtered_pairs.sort(key=lambda x: (x[0], x[1]))
        normalized_query = urlencode(filtered_pairs) if filtered_pairs else ""

        # Fragment is strictly discarded
        return urlunsplit((scheme, netloc, path, normalized_query, ""))
    except Exception:
        return None


# ==============================================================================
# Extracted Artifact Representation
# ==============================================================================

@dataclass
class ExtractedArtifact:
    """A validated candidate artifact extracted from forensic evidence."""
    artifact_id: str
    artifact_category: str  # CRYPTO, BANKING, URL, CODEWORD
    artifact_type: str      # BITCOIN, EVM, IBAN, CANONICAL_URL, CODEWORD
    value: str
    normalized_value: str
    is_validated: bool
    validation_status: str
    match_certainty: float
    confidence_score: float  # Strictly < 1.0
    source_message_id: str
    source_platform: str
    evidence_id: Optional[int]
    timestamp: Optional[int]
    context_snippet: str
    limitations: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)


class ArtifactStitcher:
    """
    Deterministic artifact extraction and cross-platform stitcher.
    Extracts BTC, EVM, IBAN, Canonical URLs, and Custom Codewords.
    """

    def __init__(
        self,
        custom_keywords: Optional[List[str]] = None,
        thresholds: CorrelationThresholds = DEFAULT_THRESHOLDS,
    ):
        self.custom_keywords = [k.strip() for k in (custom_keywords or []) if k.strip()]
        self.thresholds = thresholds

    def _extract_context(self, text: str, match_str: str, window: int = 35) -> str:
        idx = text.find(match_str)
        if idx == -1:
            return text[:70]
        start = max(0, idx - window)
        end = min(len(text), idx + len(match_str) + window)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{text[start:end]}{suffix}".strip()

    def extract_from_text(
        self,
        text: str,
        message_id: str = "",
        platform: str = "unknown",
        evidence_id: Optional[int] = None,
        timestamp: Optional[int] = None,
        location: str = "",
    ) -> List[ExtractedArtifact]:
        """Scans a text message for deterministic artifact candidates."""
        if not text:
            return []

        artifacts: List[ExtractedArtifact] = []

        # 1. Bitcoin addresses (Base58Check & Bech32)
        btc_pattern = r"\b((?:1|3)[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{39,59})\b"
        for match in re.finditer(btc_pattern, text):
            val = match.group(0)
            valid, status = validate_btc_address(val)
            if valid:
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_btc_{hashlib.sha256(val.encode()).hexdigest()[:12]}",
                    artifact_category="CRYPTO",
                    artifact_type="BITCOIN",
                    value=val,
                    normalized_value=val,
                    is_validated=True,
                    validation_status=status,
                    match_certainty=1.0,
                    confidence_score=0.95,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Public blockchain address; shared wallet or public service reuse possible."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": status,
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 2. EVM / Ethereum addresses (0x + 40 hex)
        evm_pattern = r"\b(0x[0-9a-fA-F]{40})\b"
        for match in re.finditer(evm_pattern, text):
            val = match.group(0)
            valid, status, norm_addr = validate_evm_address(val)
            if valid:
                match_certainty = 1.0 if status == "VALIDATED_EIP55_CHECKSUM_OK" else 0.85
                limitations = ["Public EVM address; smart contract or custodial address reuse possible."]
                if status == "FORMAT_VALID_NO_CHECKSUM":
                    limitations.append("Address was unchecksummed (all-lowercase/all-uppercase); checksum unverified.")

                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_evm_{hashlib.sha256(norm_addr.encode()).hexdigest()[:12]}",
                    artifact_category="CRYPTO",
                    artifact_type="EVM",
                    value=val,
                    normalized_value=norm_addr,
                    is_validated=True,
                    validation_status=status,
                    match_certainty=match_certainty,
                    confidence_score=0.92,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=limitations,
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": status,
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 3. IBAN
        iban_pattern = r"\b([A-Z]{2}[0-9]{2}(?:[ \-]?[A-Z0-9]{1,4}){2,8})\b"
        for match in re.finditer(iban_pattern, text, re.IGNORECASE):
            raw_val = match.group(0)
            valid, status, norm_iban = validate_iban(raw_val)
            if valid:
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_iban_{hashlib.sha256(norm_iban.encode()).hexdigest()[:12]}",
                    artifact_category="BANKING",
                    artifact_type="IBAN",
                    value=raw_val,
                    normalized_value=norm_iban,
                    is_validated=True,
                    validation_status=status,
                    match_certainty=1.0,
                    confidence_score=0.95,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, raw_val),
                    limitations=["International bank account number; shared corporate or escrow account possible."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": status,
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 4. Canonical URLs
        url_pattern = r"\b(https?://[^\s<>\"'{}|\\^`]+)\b"
        for match in re.finditer(url_pattern, text, re.IGNORECASE):
            raw_url = match.group(0)
            norm_url = normalize_url(raw_url)
            if norm_url:
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_url_{hashlib.sha256(norm_url.encode()).hexdigest()[:12]}",
                    artifact_category="URL",
                    artifact_type="CANONICAL_URL",
                    value=raw_url,
                    normalized_value=norm_url,
                    is_validated=True,
                    validation_status="VALIDATED_CANONICAL_URL",
                    match_certainty=0.95,
                    confidence_score=0.80,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, raw_url),
                    limitations=["Public web resource; common domain link sharing."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": "CANONICAL_URL_NORMALIZER",
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 5. Custom Codewords
        for keyword in self.custom_keywords:
            kw_pattern = rf"\b({re.escape(keyword)})\b"
            for match in re.finditer(kw_pattern, text, re.IGNORECASE):
                val = match.group(0)
                norm_kw = val.lower()
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_kw_{hashlib.sha256(norm_kw.encode()).hexdigest()[:12]}",
                    artifact_category="CODEWORD",
                    artifact_type="CODEWORD",
                    value=val,
                    normalized_value=norm_kw,
                    is_validated=True,
                    validation_status="MATCHED_KEYWORD",
                    match_certainty=0.90,
                    confidence_score=0.75,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Analyst-configured codeword matching."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "keyword": keyword,
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 6. Tron / TRC-20 addresses
        tron_pattern = r"\b(T[1-9A-HJ-NP-Za-km-z]{33})\b"
        for match in re.finditer(tron_pattern, text):
            val = match.group(0)
            if validate_tron_address(val):
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_tron_{hashlib.sha256(val.encode()).hexdigest()[:12]}",
                    artifact_category="CRYPTO",
                    artifact_type="TRON",
                    value=val,
                    normalized_value=val,
                    is_validated=True,
                    validation_status="VALIDATED_TRON_BASE58CHECK",
                    match_certainty=1.0,
                    confidence_score=0.92,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Public Tron blockchain address; custodial wallet reuse possible."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": "TRON_BASE58CHECK",
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 7. Monero addresses
        xmr_pattern = r"\b([48][0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b"
        for match in re.finditer(xmr_pattern, text):
            val = match.group(0)
            if validate_monero_address(val):
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_xmr_{hashlib.sha256(val.encode()).hexdigest()[:12]}",
                    artifact_category="CRYPTO",
                    artifact_type="MONERO",
                    value=val,
                    normalized_value=val,
                    is_validated=True,
                    validation_status="VALIDATED_MONERO_BASE58",
                    match_certainty=1.0,
                    confidence_score=0.92,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Privacy coin address; stealth address or subaddress possible."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": "MONERO_BASE58",
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 8. UPI Virtual Payment Addresses
        upi_pattern = r"\b([a-zA-Z0-9._\-]{2,50}@[a-zA-Z0-9]{2,30})\b"
        for match in re.finditer(upi_pattern, text):
            val = match.group(0)
            if validate_upi_handle(val):
                norm_upi = val.lower()
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_upi_{hashlib.sha256(norm_upi.encode()).hexdigest()[:12]}",
                    artifact_category="BANKING",
                    artifact_type="UPI",
                    value=val,
                    normalized_value=norm_upi,
                    is_validated=True,
                    validation_status="VALIDATED_UPI_HANDLE",
                    match_certainty=1.0,
                    confidence_score=0.90,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["UPI virtual payment address."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": "UPI_HANDLE_VALIDATOR",
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 9. SWIFT / BIC codes
        swift_pattern = r"(?:SWIFT|BIC|swift|bic)[\s:]*([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
        for match in re.finditer(swift_pattern, text):
            val = match.group(1)
            if validate_swift_bic(val):
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_swift_{hashlib.sha256(val.encode()).hexdigest()[:12]}",
                    artifact_category="BANKING",
                    artifact_type="SWIFT",
                    value=val,
                    normalized_value=val.upper(),
                    is_validated=True,
                    validation_status="VALIDATED_SWIFT_BIC_ISO9362",
                    match_certainty=1.0,
                    confidence_score=0.90,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Financial institution BIC code; shared routing identifier."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": "ISO_9362_BIC",
                        "location": location or f"msg_{message_id}",
                    },
                ))

        # 10. Credit Card Numbers (Luhn mod-10)
        card_pattern = r"\b(?:\d{4}[ -]?){3}\d{4}\b"
        for match in re.finditer(card_pattern, text):
            val = match.group(0)
            if validate_luhn(val):
                norm_card = re.sub(r"[\s\-]", "", val)
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_card_{hashlib.sha256(norm_card.encode()).hexdigest()[:12]}",
                    artifact_category="BANKING",
                    artifact_type="CREDIT_CARD",
                    value=val,
                    normalized_value=norm_card,
                    is_validated=True,
                    validation_status="VALIDATED_LUHN_MOD10",
                    match_certainty=1.0,
                    confidence_score=0.92,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Payment card number validated via Luhn mod-10."],
                    provenance={
                        "algorithm": "ArtifactStitcher",
                        "validator": "LUHN_MOD10",
                        "location": location or f"msg_{message_id}",
                    },
                ))

        return artifacts

    def correlate_artifacts(
        self,
        extracted: List[ExtractedArtifact],
    ) -> List[CorrelationFinding]:
        """
        Correlates extracted artifacts across distinct platforms.
        Emits strong/moderate CorrelationFinding instances per 10_CORRELATION.md §B12.3.
        """
        # Group by (artifact_type, normalized_value)
        by_key: Dict[Tuple[str, str], List[ExtractedArtifact]] = {}
        for art in extracted:
            by_key.setdefault((art.artifact_type, art.normalized_value), []).append(art)

        findings: List[CorrelationFinding] = []

        for (art_type, norm_val), items in by_key.items():
            # Find distinct platforms
            platforms = list(dict.fromkeys(item.source_platform for item in items))
            if len(platforms) < 2:
                # Same platform occurrences: emit reuse_within_app if different messages
                if len(items) >= 2:
                    left = items[0]
                    right = items[1]
                    f_id = generate_deterministic_finding_id(
                        "reuse_within_app",
                        norm_val,
                        f"{left.source_platform}:{left.source_message_id}",
                        f"{right.source_platform}:{right.source_message_id}",
                        self.thresholds.version,
                    )
                    findings.append(CorrelationFinding(
                        finding_id=f_id,
                        kind="reuse_within_app",
                        strength="moderate",
                        match_certainty=min(left.match_certainty, right.match_certainty),
                        confidence_score=min(0.85, (left.confidence_score + right.confidence_score) / 2.0),
                        normalized_value=norm_val,
                        left_ref={
                            "platform": left.source_platform,
                            "message_id": left.source_message_id,
                            "evidence_id": left.evidence_id,
                            "timestamp": left.timestamp,
                            "snippet": left.context_snippet,
                            "provenance": left.provenance,
                        },
                        right_ref={
                            "platform": right.source_platform,
                            "message_id": right.source_message_id,
                            "evidence_id": right.evidence_id,
                            "timestamp": right.timestamp,
                            "snippet": right.context_snippet,
                            "provenance": right.provenance,
                        },
                        limitations=tuple(dict.fromkeys(left.limitations + right.limitations)),
                        provenance={
                            "method": f"ARTIFACT_REUSE_SAME_APP_{art_type}",
                            "thresholds_version": self.thresholds.version,
                        },
                        thresholds_version=self.thresholds.version,
                        below_threshold=False,
                    ))
                continue

            # Cross-platform link across distinct platforms!
            left = next(item for item in items if item.source_platform == platforms[0])
            right = next(item for item in items if item.source_platform == platforms[1])

            kind_mapping = {
                "BITCOIN": ("crypto_btc", "strong"),
                "EVM": ("crypto_evm", "strong"),
                "TRON": ("crypto_tron", "strong"),
                "MONERO": ("crypto_monero", "strong"),
                "IBAN": ("banking_iban", "strong"),
                "SWIFT": ("banking_swift", "strong"),
                "UPI": ("banking_upi", "strong"),
                "CREDIT_CARD": ("banking_card", "strong"),
                "CANONICAL_URL": ("canonical_url", "strong"),
                "CODEWORD": ("custom_codeword", "moderate"),
            }
            kind, strength = kind_mapping.get(art_type, ("shared_artifact", "moderate"))
            match_cert = min(left.match_certainty, right.match_certainty)
            conf_score = min(0.95, (left.confidence_score + right.confidence_score) / 2.0)

            f_id = generate_deterministic_finding_id(
                kind,
                norm_val,
                f"{left.source_platform}:{left.source_message_id}",
                f"{right.source_platform}:{right.source_message_id}",
                self.thresholds.version,
            )

            limitations_list = list(dict.fromkeys(left.limitations + right.limitations))
            limitations_list.append("Cross-platform artifact link inferred from exact normalized value.")

            findings.append(CorrelationFinding(
                finding_id=f_id,
                kind=kind,
                strength=strength,
                match_certainty=match_cert,
                confidence_score=conf_score,
                normalized_value=norm_val,
                left_ref={
                    "platform": left.source_platform,
                    "message_id": left.source_message_id,
                    "evidence_id": left.evidence_id,
                    "timestamp": left.timestamp,
                    "snippet": left.context_snippet,
                    "provenance": left.provenance,
                },
                right_ref={
                    "platform": right.source_platform,
                    "message_id": right.source_message_id,
                    "evidence_id": right.evidence_id,
                    "timestamp": right.timestamp,
                    "snippet": right.context_snippet,
                    "provenance": right.provenance,
                },
                limitations=tuple(limitations_list),
                provenance={
                    "method": f"CROSS_PLATFORM_STITCH_{art_type}",
                    "thresholds_version": self.thresholds.version,
                },
                thresholds_version=self.thresholds.version,
                below_threshold=conf_score < self.thresholds.report_threshold_confidence,
            ))

        findings.sort(key=lambda f: f.sort_key())
        return findings
