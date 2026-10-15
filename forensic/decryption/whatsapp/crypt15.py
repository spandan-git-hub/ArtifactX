"""
WhatsApp Crypt15 Forensic Decryption Engine.
Strictly adheres to:
- master.md R4: Zero disk writes; pure in-memory streaming/buffers.
- master.md R5: Keys are radioactive. Redacted strings, zeroing, no logging.
- master.md R7: No fake capability. Decrypts only with valid key material.
- master.md R12: Untrusted input hardening; capped decompression.
- master.md R15: Zero GPL code, independent implementation.
- DEC-002: Passphrases rejected offline with PassphraseNotSupported.
- spec 04_WHATSAPP_DECRYPTION.md §B6.2.
"""

from __future__ import annotations

import hashlib
import zlib
from typing import Any, Dict, Optional, Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from forensic.decryption.whatsapp.errors import (
    DecryptionAuthFailed,
    DecompressionFailed,
    TruncatedInput,
    UnsupportedVersion,
)
from forensic.decryption.whatsapp.keys import WhatsAppKeyParser
from forensic.decryption.whatsapp.protobuf_min import ProtobufReader
from forensic.decryption.whatsapp.types import DecryptionResult, KeyMaterial
from forensic.decryption.whatsapp.validate import validate_decrypted_payload

DEFAULT_MAX_DECOMPRESSED_SIZE = 256 * 1024 * 1024  # 256 MiB per DEC-009 / DEC-021


class Crypt15Decryptor:
    """Independent implementation of WhatsApp Crypt15 backup decryptor."""

    format_id: str = "crypt15"

    def __init__(self, max_decompressed_size: int = DEFAULT_MAX_DECOMPRESSED_SIZE):
        self.max_decompressed_size = max_decompressed_size

    def can_handle(self, header: bytes, filename: Optional[str] = None) -> bool:
        """Inspect header or filename to determine if this engine handles the container."""
        if filename and filename.lower().endswith(".crypt15"):
            return True
        try:
            parsed = ProtobufReader.parse_header(header)
            return parsed.format_id == "crypt15"
        except Exception:
            return False

    def decrypt(
        self,
        data: bytes,
        key_material: Union[KeyMaterial, bytes, str],
        max_decompressed_size: Optional[int] = None,
    ) -> DecryptionResult:
        """
        Execute in-memory Crypt15 decryption and forensic validation.
        """
        if not data:
            raise TruncatedInput("Encrypted buffer is empty.")

        # 1. Parse container header
        try:
            hdr = ProtobufReader.parse_header(data)
        except Exception as exc:
            raise UnsupportedVersion(f"Failed to parse crypt15 container header: {exc}") from exc

        if hdr.format_id != "crypt15":
            raise UnsupportedVersion(
                f"Expected crypt15 container, but parsed header identified format as '{hdr.format_id}'."
            )

        if len(hdr.iv) != 16:
            raise TruncatedInput(f"Invalid IV length in header: {len(hdr.iv)} bytes (expected 16).")

        # 2. Check length requirements (header + ciphertext + 16B tag + 16B trailer checksum)
        min_required = hdr.header_size + 32
        if len(data) < min_required:
            raise TruncatedInput(
                f"Crypt15 buffer length {len(data)} is shorter than minimum required {min_required} bytes."
            )

        # 3. Parse components
        checksum_trailer = data[-16:]
        auth_tag = data[-32:-16]
        ciphertext = data[hdr.header_size : -32]

        # Verify MD5 trailer checksum over (header + ciphertext + tag)
        computed_md5 = hashlib.md5(data[:-16]).digest()
        checksum_ok = (computed_md5 == checksum_trailer)

        # 4. Parse key material (DEC-002: passphrases rejected)
        root_km, cipher_km = WhatsAppKeyParser.parse_crypt15_key(key_material)
        aes_key = cipher_km.raw_key

        try:
            # 5. Decrypt using AES-256-GCM
            aesgcm = AESGCM(aes_key)
            try:
                # AESGCM.decrypt expects ciphertext || auth_tag
                compressed_plaintext = aesgcm.decrypt(
                    nonce=hdr.iv,
                    data=ciphertext + auth_tag,
                    associated_data=None,
                )
            except InvalidTag as it:
                raise DecryptionAuthFailed(
                    "Authentication failed: wrong key OR modified/corrupted data."
                ) from it
            except Exception as e:
                raise DecryptionAuthFailed(
                    f"Authentication failed: wrong key OR modified/corrupted data ({e})."
                ) from e

            # 6. Decompress zlib payload with safety ceiling
            cap = max_decompressed_size or self.max_decompressed_size
            try:
                decompressor = zlib.decompressobj()
                decompressed = decompressor.decompress(compressed_plaintext, cap)
                if not decompressor.eof:
                    # Check if there is remaining data exceeding cap
                    if len(decompressor.unconsumed_tail) > 0 or len(decompressed) >= cap:
                        raise DecompressionFailed(
                            f"Decompressed output exceeds safety memory ceiling of {cap} bytes."
                        )
            except zlib.error as ze:
                raise DecompressionFailed(f"Zlib decompression failed: {ze}") from ze

            # 7. Post-decryption validation pipeline
            report = validate_decrypted_payload(
                plaintext_decompressed=decompressed,
                gcm_auth_ok=True,
                zlib_decompress_ok=True,
                checksum_ok=checksum_ok,
                enforce_whatsapp_schema=False,
            )

            out_sha256 = hashlib.sha256(decompressed).hexdigest()
            meta: Dict[str, Any] = {
                "format": "crypt15",
                "header_size": hdr.header_size,
                "app_version": hdr.app_version,
                "jid_suffix": hdr.jid_suffix,
                "key_fingerprint": root_km.fingerprint(),
                "checksum_ok": checksum_ok,
                "validation": {
                    "is_valid_sqlite": report.is_valid_sqlite,
                    "schema_family": report.schema_family,
                    "whatsapp_schema_ok": report.whatsapp_schema_ok,
                    "tables": report.details.get("tables", []),
                },
            }

            return DecryptionResult(
                plaintext=decompressed,
                format_id="crypt15",
                output_sha256=out_sha256,
                validation_report=report,
                metadata=meta,
            )

        finally:
            # R5: Best-effort memory zeroing of secret keys
            root_km.zero()
            cipher_km.zero()
