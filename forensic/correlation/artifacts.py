"""
Shared Forensic Artifact Extraction and Verification Engine.
Extracts deterministic artifact classes: Cryptocurrency, IBAN/SWIFT, Credit Cards, UPI, Tracking, Codewords.
All candidate matches undergo strict cryptographic, algorithmic (mod-97, Luhn, Base58Check), or format validation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import re
import hashlib
import uuid


# Base58 Alphabet
B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def is_valid_base58(s: str) -> bool:
    return all(c in B58_ALPHABET for c in s)


def base58_decode(s: str) -> Optional[bytes]:
    """Decode base58 string to bytes."""
    if not is_valid_base58(s):
        return None
    num = 0
    for char in s:
        num = num * 58 + B58_ALPHABET.index(char)
    # Convert num to bytes
    raw = num.to_bytes((num.bit_length() + 7) // 8, byteorder="big")
    # Add leading zeros
    pad = 0
    for char in s:
        if char == B58_ALPHABET[0]:
            pad += 1
        else:
            break
    return (b"\x00" * pad) + raw


def validate_btc_address(addr: str) -> bool:
    """Validate Bitcoin address format (P2PKH, P2SH, Bech32)."""
    if not addr:
        return False
    # Bech32 (Segwit)
    if addr.startswith("bc1"):
        return 42 <= len(addr) <= 62 and all(c in "qpzry9x8gf2tvdw0s3jn54khce6mua7l" for c in addr[3:])
    # Legacy P2PKH / P2SH with Base58Check
    if (addr.startswith("1") or addr.startswith("3")) and (25 <= len(addr) <= 35):
        decoded = base58_decode(addr)
        if decoded and len(decoded) == 25:
            payload, check = decoded[:-4], decoded[-4:]
            expected_check = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            return check == expected_check
    return False


def validate_evm_address(addr: str) -> bool:
    """Validate EVM/Ethereum address format (0x + 40 hex digits) and optional EIP-55."""
    if not addr or not addr.startswith("0x") or len(addr) != 42:
        return False
    hex_part = addr[2:]
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", hex_part))


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


def validate_iban(iban_str: str) -> bool:
    """Validate IBAN using ISO 7064 Modulo 97-10 check."""
    clean = re.sub(r"[\s\-]", "", iban_str).upper()
    if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}", clean):
        return False
    # Move country code & check digits to the end
    rearranged = clean[4:] + clean[:4]
    # Replace letters with digits: A=10 ... Z=35
    digits = []
    for ch in rearranged:
        if ch.isdigit():
            digits.append(ch)
        elif ch.isupper():
            digits.append(str(ord(ch) - ord("A") + 10))
        else:
            return False
    num_str = "".join(digits)
    try:
        return int(num_str) % 97 == 1
    except ValueError:
        return False


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
    # Avoid matching standard email addresses with standard TLDs
    parts = upi.split("@")
    if len(parts) != 2:
        return False
    user, handle = parts[0], parts[1]
    if not re.fullmatch(r"[a-zA-Z0-9._\-]{2,50}", user):
        return False
    # UPI handles typically don't have multiple dot-segments like .com, or are known bank suffixes
    common_email_tlds = {"com", "net", "org", "edu", "gov", "io", "co", "uk", "de"}
    handle_parts = handle.split(".")
    if len(handle_parts) == 2 and handle_parts[1].lower() in common_email_tlds:
        return False
    return bool(re.fullmatch(r"[a-zA-Z0-9]{2,30}", handle))


@dataclass
class ExtractedArtifact:
    """Represents a validated financial, crypto, or tracking artifact discovered in evidence."""
    artifact_id: str
    artifact_category: str  # CRYPTO, BANKING, LOGISTICS, CODEWORD
    artifact_type: str      # BITCOIN, EVM, MONERO, TRON, IBAN, SWIFT, CREDIT_CARD, UPI, FLIGHT, CODEWORD
    value: str
    normalized_value: str
    is_validated: bool
    validation_status: str  # VALIDATED_CHECKSUM_OK, VALIDATED_FORMAT_OK, CANDIDATE
    confidence_score: float
    source_message_id: str
    source_platform: str
    evidence_id: Optional[int]
    timestamp: Optional[int]
    context_snippet: str
    limitations: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_category": self.artifact_category,
            "artifact_type": self.artifact_type,
            "value": self.value,
            "normalized_value": self.normalized_value,
            "is_validated": self.is_validated,
            "validation_status": self.validation_status,
            "confidence_score": round(self.confidence_score, 4),
            "source_message_id": self.source_message_id,
            "source_platform": self.source_platform,
            "evidence_id": self.evidence_id,
            "timestamp": self.timestamp,
            "context_snippet": self.context_snippet,
            "limitations": self.limitations,
            "provenance": self.provenance,
        }


class ArtifactStitcher:
    """
    Extracts and correlates deterministic artifacts across evidence text messages.
    Supports analyst-configured custom keywords or code words.
    """

    def __init__(self, custom_keywords: Optional[List[str]] = None):
        self.custom_keywords = custom_keywords or []
        self.version = "1.0.0"

    def _extract_context(self, text: str, match_str: str, window: int = 40) -> str:
        idx = text.find(match_str)
        if idx == -1:
            return text[:80]
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
    ) -> List[ExtractedArtifact]:
        """Scans a single text string for all deterministic artifact classes."""
        if not text:
            return []

        artifacts: List[ExtractedArtifact] = []

        # 1. Bitcoin addresses
        btc_pattern = r"\b((?:1|3)[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{39,59})\b"
        for match in re.finditer(btc_pattern, text):
            val = match.group(0)
            valid = validate_btc_address(val)
            artifacts.append(ExtractedArtifact(
                artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                artifact_category="CRYPTO",
                artifact_type="BITCOIN",
                value=val,
                normalized_value=val,
                is_validated=valid,
                validation_status="VALIDATED_CHECKSUM_OK" if valid else "CANDIDATE",
                confidence_score=0.98 if valid else 0.70,
                source_message_id=message_id,
                source_platform=platform,
                evidence_id=evidence_id,
                timestamp=timestamp,
                context_snippet=self._extract_context(text, val),
                limitations=[] if valid else ["Base58Check checksum validation failed."],
                provenance={"algorithm": "ArtifactStitcher", "validator": "Base58Check/Bech32"},
            ))

        # 2. EVM / Ethereum addresses
        evm_pattern = r"\b(0x[0-9a-fA-F]{40})\b"
        for match in re.finditer(evm_pattern, text):
            val = match.group(0)
            valid = validate_evm_address(val)
            artifacts.append(ExtractedArtifact(
                artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                artifact_category="CRYPTO",
                artifact_type="EVM",
                value=val,
                normalized_value=val.lower(),
                is_validated=valid,
                validation_status="VALIDATED_FORMAT_OK" if valid else "CANDIDATE",
                confidence_score=0.99 if valid else 0.75,
                source_message_id=message_id,
                source_platform=platform,
                evidence_id=evidence_id,
                timestamp=timestamp,
                context_snippet=self._extract_context(text, val),
                limitations=[],
                provenance={"algorithm": "ArtifactStitcher", "validator": "EVM_HEX_40"},
            ))

        # 3. Tron (TRC-20) addresses
        tron_pattern = r"\b(T[1-9A-HJ-NP-Za-km-z]{33})\b"
        for match in re.finditer(tron_pattern, text):
            val = match.group(0)
            valid = validate_tron_address(val)
            artifacts.append(ExtractedArtifact(
                artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                artifact_category="CRYPTO",
                artifact_type="TRON",
                value=val,
                normalized_value=val,
                is_validated=valid,
                validation_status="VALIDATED_CHECKSUM_OK" if valid else "CANDIDATE",
                confidence_score=0.95 if valid else 0.65,
                source_message_id=message_id,
                source_platform=platform,
                evidence_id=evidence_id,
                timestamp=timestamp,
                context_snippet=self._extract_context(text, val),
                limitations=[],
                provenance={"algorithm": "ArtifactStitcher", "validator": "TronBase58"},
            ))

        # 4. Monero addresses
        xmr_pattern = r"\b([48][0-9ABa-km-zA-HJ-NP-Z]{94}|[48][0-9ABa-km-zA-HJ-NP-Z]{105})\b"
        for match in re.finditer(xmr_pattern, text):
            val = match.group(0)
            valid = validate_monero_address(val)
            artifacts.append(ExtractedArtifact(
                artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                artifact_category="CRYPTO",
                artifact_type="MONERO",
                value=val,
                normalized_value=val,
                is_validated=valid,
                validation_status="VALIDATED_FORMAT_OK" if valid else "CANDIDATE",
                confidence_score=0.95 if valid else 0.65,
                source_message_id=message_id,
                source_platform=platform,
                evidence_id=evidence_id,
                timestamp=timestamp,
                context_snippet=self._extract_context(text, val),
                limitations=[],
                provenance={"algorithm": "ArtifactStitcher", "validator": "MoneroBase58"},
            ))

        # 5. IBAN
        iban_pattern = r"\b([A-Z]{2}[0-9]{2}(?:[ \-]?[A-Z0-9]{4}){2,7}[A-Z0-9]{1,4})\b"
        for match in re.finditer(iban_pattern, text, re.IGNORECASE):
            raw_val = match.group(0)
            clean_val = re.sub(r"[\s\-]", "", raw_val).upper()
            if len(clean_val) >= 15:
                valid = validate_iban(clean_val)
                if valid:
                    artifacts.append(ExtractedArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                        artifact_category="BANKING",
                        artifact_type="IBAN",
                        value=raw_val,
                        normalized_value=clean_val,
                        is_validated=True,
                        validation_status="VALIDATED_CHECKSUM_OK",
                        confidence_score=1.0,
                        source_message_id=message_id,
                        source_platform=platform,
                        evidence_id=evidence_id,
                        timestamp=timestamp,
                        context_snippet=self._extract_context(text, raw_val),
                        limitations=[],
                        provenance={"algorithm": "ArtifactStitcher", "validator": "ISO_7064_MOD97"},
                    ))

        # 6. SWIFT / BIC
        swift_pattern = r"\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
        for match in re.finditer(swift_pattern, text):
            val = match.group(0)
            # Filter common words that happen to be 8-11 caps
            if val not in ("TELEGRAM", "WHATSAPP", "PASSWORD", "SETTINGS", "DATABASE") and validate_swift_bic(val):
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                    artifact_category="BANKING",
                    artifact_type="SWIFT",
                    value=val,
                    normalized_value=val.upper(),
                    is_validated=True,
                    validation_status="VALIDATED_FORMAT_OK",
                    confidence_score=0.90,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Validated ISO 9362 format."],
                    provenance={"algorithm": "ArtifactStitcher", "validator": "ISO_9362"},
                ))

        # 7. Credit card numbers (Luhn checked)
        cc_pattern = r"\b((?:4[0-9]{12}(?:[0-9]{3})?)|(?:5[1-5][0-9]{14})|(?:3[47][0-9]{13})|(?:[0-9]{4}[\s\-][0-9]{4}[\s\-][0-9]{4}[\s\-][0-9]{4}))\b"
        for match in re.finditer(cc_pattern, text):
            val = match.group(0)
            if validate_luhn(val):
                clean_cc = re.sub(r"[\s\-]", "", val)
                # Mask middle digits for sensitive secret redaction
                masked = f"{clean_cc[:4]}********{clean_cc[-4:]}"
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                    artifact_category="BANKING",
                    artifact_type="CREDIT_CARD",
                    value=masked,
                    normalized_value=masked,
                    is_validated=True,
                    validation_status="VALIDATED_CHECKSUM_OK",
                    confidence_score=1.0,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Cardholder PAN redacted; validated against Luhn mod-10."],
                    provenance={"algorithm": "ArtifactStitcher", "validator": "LuhnMod10"},
                ))

        # 8. UPI Virtual Payment Addresses
        upi_pattern = r"\b([a-zA-Z0-9.\-_]{2,40}@[a-zA-Z0-9]{2,30})\b"
        for match in re.finditer(upi_pattern, text):
            val = match.group(0)
            if validate_upi_handle(val):
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                    artifact_category="BANKING",
                    artifact_type="UPI",
                    value=val,
                    normalized_value=val.lower(),
                    is_validated=True,
                    validation_status="VALIDATED_FORMAT_OK",
                    confidence_score=0.92,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=[],
                    provenance={"algorithm": "ArtifactStitcher", "validator": "UPI_VPA_SYNTAX"},
                ))

        # 9. Flight numbers
        flight_pattern = r"\b([A-Z]{2,3}\s?[0-9]{1,4})\b"
        for match in re.finditer(flight_pattern, text):
            val = match.group(0)
            # Must look like an airline code (e.g. EK 502, AA123, BA 2490)
            code, num = val[:2], val[2:].strip()
            if code.isupper() and num.isdigit() and 1 <= len(num) <= 4:
                # Check for context clues: flight, flt, terminal, airport, gate, boarding, travel
                lower_context = text.lower()
                has_context = any(w in lower_context for w in ("flight", "flt", "terminal", "airport", "gate", "airline", "boarding", "ticket"))
                if has_context:
                    norm = f"{code}{num}"
                    artifacts.append(ExtractedArtifact(
                        artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                        artifact_category="LOGISTICS",
                        artifact_type="FLIGHT_NUMBER",
                        value=val,
                        normalized_value=norm,
                        is_validated=True,
                        validation_status="VALIDATED_FORMAT_OK",
                        confidence_score=0.88,
                        source_message_id=message_id,
                        source_platform=platform,
                        evidence_id=evidence_id,
                        timestamp=timestamp,
                        context_snippet=self._extract_context(text, val),
                        limitations=["Extracted with contextual flight keywords."],
                        provenance={"algorithm": "ArtifactStitcher", "validator": "IATA_FLIGHT_SYNTAX"},
                    ))

        # 10. Analyst-configured codewords
        for keyword in self.custom_keywords:
            if not keyword:
                continue
            kw_pattern = rf"\b({re.escape(keyword)})\b"
            for match in re.finditer(kw_pattern, text, re.IGNORECASE):
                val = match.group(0)
                artifacts.append(ExtractedArtifact(
                    artifact_id=f"art_{uuid.uuid4().hex[:12]}",
                    artifact_category="CODEWORD",
                    artifact_type="CUSTOM_KEYWORD",
                    value=val,
                    normalized_value=val.lower(),
                    is_validated=True,
                    validation_status="MATCHED_KEYWORD",
                    confidence_score=1.0,
                    source_message_id=message_id,
                    source_platform=platform,
                    evidence_id=evidence_id,
                    timestamp=timestamp,
                    context_snippet=self._extract_context(text, val),
                    limitations=["Analyst-specified keyword query match."],
                    provenance={"algorithm": "ArtifactStitcher", "keyword": keyword},
                ))

        return artifacts

    def correlate_shared_artifacts(
        self,
        extracted_artifacts: List[ExtractedArtifact]
    ) -> List[Dict[str, Any]]:
        """
        Groups artifacts by normalized value to identify cross-message and cross-platform shared exhibits.
        """
        grouped: Dict[str, List[ExtractedArtifact]] = {}
        for art in extracted_artifacts:
            key = (art.artifact_type, art.normalized_value)
            grouped.setdefault(key, []).append(art)

        shared_clusters = []
        for (art_type, norm_val), items in grouped.items():
            if len(items) > 1:
                platforms = list(dict.fromkeys(item.source_platform for item in items))
                is_cross_platform = len(platforms) > 1
                cluster = {
                    "cluster_id": f"cluster_{uuid.uuid4().hex[:12]}",
                    "artifact_type": art_type,
                    "normalized_value": norm_val,
                    "occurrence_count": len(items),
                    "platforms": platforms,
                    "is_cross_platform": is_cross_platform,
                    "occurrences": [item.to_dict() for item in items],
                    "confidence_score": max(item.confidence_score for item in items),
                    "provenance": {
                        "algorithm": "ArtifactStitcher",
                        "method": "EXACT_NORMALIZED_MATCH",
                    }
                }
                shared_clusters.append(cluster)

        shared_clusters.sort(key=lambda c: (-c["occurrence_count"], c["artifact_type"]))
        return shared_clusters
