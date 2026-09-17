"""
WhatsApp Crypt15 Database Decryptor.
Implements End-to-End Encrypted backup decryption using 64-character hex passkey,
PBKDF2-HMAC-SHA512 key derivation (100,000 iterations), AES-256-GCM, and SQLite verification.
"""

import binascii
import hashlib
import zlib
from typing import Dict, Optional, Tuple, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from forensic.decryption.whatsapp.key_parser import WhatsAppKey, WhatsAppKeyParser
from forensic.decryption.whatsapp.validator import SQLiteValidator


class Crypt15Decryptor:
    """Decryptor for WhatsApp .crypt15 cloud and local passkey backups."""

    HEADER_SIZE = 67
    SALT_OFFSET = 16
    SALT_LENGTH = 32
    IV_OFFSET = 51
    IV_LENGTH = 16
    DEFAULT_ITERATIONS = 100000

    @classmethod
    def derive_key(cls, passkey_bytes: bytes, salt: bytes, iterations: int = DEFAULT_ITERATIONS) -> bytes:
        """Derive AES-256 key using PBKDF2-HMAC-SHA512."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(passkey_bytes)

    @classmethod
    def decrypt(
        cls,
        encrypted_data: bytes,
        passkey: Union[WhatsAppKey, str, bytes],
        iterations: int = DEFAULT_ITERATIONS,
    ) -> Tuple[bytes, Dict]:
        """
        Decrypt WhatsApp Crypt15 container using 64-hex passkey.
        Returns: (plaintext_sqlite_bytes, operation_provenance_metadata)
        """
        if len(encrypted_data) < cls.HEADER_SIZE + 16:
            raise ValueError(
                f"Crypt15 payload too short: {len(encrypted_data)} bytes. "
                f"Minimum required is {cls.HEADER_SIZE + 16} bytes."
            )

        # Normalize passkey input without logging
        if isinstance(passkey, WhatsAppKey):
            raw_passkey = passkey.cipher_key
        elif isinstance(passkey, str):
            clean = passkey.strip().replace(" ", "").replace("-", "")
            raw_passkey = binascii.unhexlify(clean) if len(clean) == 64 else clean.encode("utf-8")
        else:
            raw_passkey = bytes(passkey)

        input_sha256 = hashlib.sha256(encrypted_data).hexdigest()

        # 1. Extract salt and IV from header
        salt = encrypted_data[cls.SALT_OFFSET : cls.SALT_OFFSET + cls.SALT_LENGTH]
        iv = encrypted_data[cls.IV_OFFSET : cls.IV_OFFSET + cls.IV_LENGTH]
        ciphertext_and_tag = encrypted_data[cls.HEADER_SIZE:]

        # 2. Derive AES key
        derived_key = cls.derive_key(raw_passkey, salt, iterations=iterations)

        # 3. Decrypt AES-256-GCM
        aesgcm = AESGCM(derived_key)
        try:
            decrypted_raw = aesgcm.decrypt(iv, ciphertext_and_tag, None)
        except Exception as e:
            raise ValueError(f"Crypt15 authentication failed (wrong passkey or corrupted ciphertext): {str(e)}")

        # 4. Decompress if zlib compressed
        is_compressed = False
        if decrypted_raw.startswith(b"SQLite format 3\x00"):
            plaintext_bytes = decrypted_raw
        else:
            try:
                plaintext_bytes = zlib.decompress(decrypted_raw)
                is_compressed = True
            except Exception:
                plaintext_bytes = decrypted_raw

        # 5. Validate SQLite
        val_result = SQLiteValidator.validate(plaintext_bytes)
        output_sha256 = hashlib.sha256(plaintext_bytes).hexdigest()

        metadata = {
            "format": "crypt15",
            "cipher": "AES-256-GCM",
            "kdf": "PBKDF2-HMAC-SHA512",
            "iterations": iterations,
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
        passkey_hex: str,
        compress: bool = True,
        iterations: int = 1000,  # Lower iterations for test suite speed
    ) -> bytes:
        """Synthetic fixture generator for Crypt15."""
        import os
        payload = zlib.compress(sqlite_bytes) if compress else sqlite_bytes
        salt = os.urandom(32)
        iv = os.urandom(16)

        header = b"\x00\x01crypt15\x00\x00\x00\x00\x00\x00\x00" + salt + b"\x00\x00\x00" + iv
        raw_passkey = binascii.unhexlify(passkey_hex) if len(passkey_hex) == 64 else passkey_hex.encode("utf-8")
        key = cls.derive_key(raw_passkey, salt, iterations=iterations)

        aesgcm = AESGCM(key)
        ciphertext_and_tag = aesgcm.encrypt(iv, payload, None)
        return header + ciphertext_and_tag
