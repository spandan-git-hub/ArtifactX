"""
WhatsApp Crypt14 Database Decryptor.
Implements modernized Crypt14 header parsing, PBKDF2-HMAC-SHA256 session key derivation,
AES-256-GCM decryption, and in-memory SQLite output.
"""

import hashlib
import zlib
from typing import Dict, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from forensic.decryption.whatsapp.key_parser import WhatsAppKey
from forensic.decryption.whatsapp.validator import SQLiteValidator


class Crypt14Decryptor:
    """Decryptor for WhatsApp .crypt14 database containers."""

    HEADER_SIZE = 67
    SALT_OFFSET = 16
    SALT_LENGTH = 32
    IV_OFFSET = 51
    IV_LENGTH = 16

    @classmethod
    def derive_session_key(cls, master_key: bytes, salt: bytes, iterations: int = 16) -> bytes:
        """Derive AES-256-GCM session key using PBKDF2-HMAC-SHA256."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(master_key)

    @classmethod
    def decrypt(
        cls,
        encrypted_data: bytes,
        key: WhatsAppKey,
    ) -> Tuple[bytes, Dict]:
        """
        Decrypt WhatsApp Crypt14 container into in-memory SQLite database bytes.
        Returns: (plaintext_sqlite_bytes, operation_provenance_metadata)
        """
        if len(encrypted_data) < cls.HEADER_SIZE + 16:
            raise ValueError(
                f"Crypt14 payload too short: {len(encrypted_data)} bytes. "
                f"Minimum required is {cls.HEADER_SIZE + 16} bytes."
            )

        input_sha256 = hashlib.sha256(encrypted_data).hexdigest()

        # 1. Header parsing: extract salt and IV
        salt = encrypted_data[cls.SALT_OFFSET : cls.SALT_OFFSET + cls.SALT_LENGTH]
        iv = encrypted_data[cls.IV_OFFSET : cls.IV_OFFSET + cls.IV_LENGTH]
        ciphertext_and_tag = encrypted_data[cls.HEADER_SIZE:]

        # 2. Derive session key
        session_key = cls.derive_session_key(key.cipher_key, salt)

        # 3. Decrypt with AES-256-GCM
        aesgcm = AESGCM(session_key)
        try:
            decrypted_raw = aesgcm.decrypt(iv, ciphertext_and_tag, None)
        except Exception as e:
            raise ValueError(f"Crypt14 AES-GCM authentication failed or corrupted ciphertext: {str(e)}")

        # 4. Decompression
        is_compressed = False
        if decrypted_raw.startswith(b"SQLite format 3\x00"):
            plaintext_bytes = decrypted_raw
        else:
            try:
                plaintext_bytes = zlib.decompress(decrypted_raw)
                is_compressed = True
            except Exception:
                plaintext_bytes = decrypted_raw

        # 5. Validation
        val_result = SQLiteValidator.validate(plaintext_bytes)
        output_sha256 = hashlib.sha256(plaintext_bytes).hexdigest()

        metadata = {
            "format": "crypt14",
            "cipher": "AES-256-GCM",
            "kdf": "PBKDF2-HMAC-SHA256",
            "salt_length": len(salt),
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
        """Synthetic fixture generator for Crypt14."""
        import os
        payload = zlib.compress(sqlite_bytes) if compress else sqlite_bytes
        salt = os.urandom(32)
        iv = key.iv or os.urandom(16)

        # 67-byte header:
        # [0:16] magic + version
        # [16:48] salt (32 bytes)
        # [48:51] reserved (3 bytes)
        # [51:67] IV (16 bytes)
        header = b"\x00\x01crypt14\x00\x00\x00\x00\x00\x00\x00" + salt + b"\x00\x00\x00" + iv
        session_key = cls.derive_session_key(key.cipher_key, salt)

        aesgcm = AESGCM(session_key)
        ciphertext_and_tag = aesgcm.encrypt(iv, payload, None)
        return header + ciphertext_and_tag
