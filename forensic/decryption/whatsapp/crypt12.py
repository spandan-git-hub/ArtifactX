"""
WhatsApp Crypt12 Database Decryptor.
Implements AES-256-GCM decryption with header parsing, IV extraction,
optional zlib decompression, and zero-local-disk in-memory output.
"""

import hashlib
import zlib
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from forensic.decryption.whatsapp.key_parser import WhatsAppKey
from forensic.decryption.whatsapp.validator import SQLiteValidator


class Crypt12Decryptor:
    """Decryptor for WhatsApp .crypt12 database containers."""

    HEADER_SIZE = 67
    IV_OFFSET = 51
    IV_LENGTH = 16

    @classmethod
    def decrypt(
        cls,
        encrypted_data: bytes,
        key: WhatsAppKey,
    ) -> Tuple[bytes, Dict]:
        """
        Decrypt WhatsApp Crypt12 container into in-memory SQLite database bytes.
        Returns: (plaintext_sqlite_bytes, operation_provenance_metadata)
        """
        if len(encrypted_data) < cls.HEADER_SIZE + 16:
            raise ValueError(
                f"Crypt12 payload too short: {len(encrypted_data)} bytes. "
                f"Minimum required is {cls.HEADER_SIZE + 16} bytes."
            )

        input_sha256 = hashlib.sha256(encrypted_data).hexdigest()

        # 1. Header & IV parsing
        # In standard Crypt12, IV is extracted from bytes 51 through 67 (16 bytes)
        iv = encrypted_data[cls.IV_OFFSET : cls.IV_OFFSET + cls.IV_LENGTH]
        ciphertext_and_tag = encrypted_data[cls.HEADER_SIZE:]

        # 2. AES-256-GCM Decryption
        aesgcm = AESGCM(key.cipher_key)
        try:
            decrypted_raw = aesgcm.decrypt(iv, ciphertext_and_tag, None)
        except Exception as e:
            # Check if tag is stored differently (e.g. 16-byte tag before ciphertext)
            raise ValueError(f"AES-GCM authentication failed or corrupted ciphertext: {str(e)}")

        # 3. Handle optional zlib decompression
        is_compressed = False
        if decrypted_raw.startswith(b"SQLite format 3\x00"):
            plaintext_bytes = decrypted_raw
        else:
            try:
                plaintext_bytes = zlib.decompress(decrypted_raw)
                is_compressed = True
            except Exception:
                # If zlib fails and doesn't match SQLite magic directly
                plaintext_bytes = decrypted_raw

        # 4. In-memory validation
        val_result = SQLiteValidator.validate(plaintext_bytes)
        output_sha256 = hashlib.sha256(plaintext_bytes).hexdigest()

        metadata = {
            "format": "crypt12",
            "cipher": "AES-256-GCM",
            "iv_length": len(iv),
            "compressed": is_compressed,
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "size_bytes": len(plaintext_bytes),
            "validation": val_result,
        }

        return plaintext_bytes, metadata

    @classmethod
    def create_fixture(
        cls,
        sqlite_bytes: bytes,
        key: WhatsAppKey,
        compress: bool = True,
    ) -> bytes:
        """
        Forensic synthetic fixture builder for testing.
        Constructs an authentic Crypt12 container from SQLite bytes.
        """
        import os
        payload = zlib.compress(sqlite_bytes) if compress else sqlite_bytes
        iv = key.iv or os.urandom(16)

        # 67-byte header:
        # 0..51: header magic/padding
        header_prefix = b"\x00\x01" + b"ArtifactX_Crypt12_Header" + b"\x00" * (51 - 2 - len(b"ArtifactX_Crypt12_Header"))
        header = header_prefix + iv  # total 67 bytes

        aesgcm = AESGCM(key.cipher_key)
        ciphertext_and_tag = aesgcm.encrypt(iv, payload, None)
        return header + ciphertext_and_tag
