"""
WhatsApp Key Parser.
Ingests and parses the standard 158-byte WhatsApp key file (/data/data/com.whatsapp/files/key),
raw 32-byte symmetric keys, and 64-character hex passkeys for Crypt15 backups.
Enforces zero secret leakage in string representations and logs.
"""

import binascii
from typing import Optional, Union


class WhatsAppKey:
    """
    Forensic encapsulation of WhatsApp key material.
    Ensures secret key bytes are never accidentally exposed via logging or string output.
    """

    def __init__(
        self,
        cipher_key: bytes,
        iv: Optional[bytes] = None,
        key_type: str = "CRYPT12",
        raw_source_hash: Optional[str] = None,
    ):
        if not isinstance(cipher_key, (bytes, bytearray)) or len(cipher_key) != 32:
            raise ValueError(f"Cipher key must be exactly 32 bytes (256 bits), got {len(cipher_key) if cipher_key else 0} bytes.")
        self._cipher_key = bytes(cipher_key)
        self._iv = bytes(iv) if iv else None
        self.key_type = key_type
        self.raw_source_hash = raw_source_hash

    @property
    def cipher_key(self) -> bytes:
        """Access raw 32-byte cipher key."""
        return self._cipher_key

    @property
    def iv(self) -> Optional[bytes]:
        """Access 16-byte default IV if present."""
        return self._iv

    def __repr__(self) -> str:
        # Strict judicial redaction: never display actual key bytes
        return f"<WhatsAppKey type={self.key_type} key_length=32B [SECRET REDACTED]>"

    def __str__(self) -> str:
        return self.__repr__()


class WhatsAppKeyParser:
    """Parser for seized WhatsApp key files and passkeys."""

    EXPECTED_FILE_KEY_SIZE = 158

    @classmethod
    def parse(cls, key_material: Union[bytes, str]) -> WhatsAppKey:
        """
        Parse key material from raw bytes, base64/hex string, or standard 158-byte file.
        """
        if isinstance(key_material, str):
            clean_str = key_material.strip().replace(" ", "").replace("\n", "")
            # Check if 64-hex passkey
            if len(clean_str) == 64:
                try:
                    raw_bytes = binascii.unhexlify(clean_str)
                    return WhatsAppKey(cipher_key=raw_bytes, key_type="CRYPT15_PASSKEY")
                except binascii.Error:
                    pass

            # Try base64
            try:
                import base64
                decoded = base64.b64decode(clean_str)
                if len(decoded) in (32, cls.EXPECTED_FILE_KEY_SIZE):
                    return cls.parse(decoded)
            except Exception:
                pass

            # If still str, encode utf-8
            key_material = clean_str.encode("utf-8")

        if not isinstance(key_material, (bytes, bytearray)):
            raise ValueError("Key material must be bytes or string.")

        # 1. Standard 158-byte /data/data/com.whatsapp/files/key file
        if len(key_material) == cls.EXPECTED_FILE_KEY_SIZE:
            # Bytes 30..62 (32 bytes): AES-256 Symmetric Cipher Key
            cipher_key = key_material[30:62]
            # Bytes 110..126 (16 bytes): Default IV
            iv = key_material[110:126]
            return WhatsAppKey(cipher_key=cipher_key, iv=iv, key_type="CRYPT12_14_FILE")

        # 2. Raw 32-byte key
        if len(key_material) == 32:
            return WhatsAppKey(cipher_key=bytes(key_material), key_type="RAW_32")

        # 3. 64-character ascii hex representation passed as bytes
        if len(key_material) == 64:
            try:
                raw_bytes = binascii.unhexlify(key_material)
                return WhatsAppKey(cipher_key=raw_bytes, key_type="CRYPT15_PASSKEY")
            except Exception:
                pass

        raise ValueError(
            f"Invalid WhatsApp key material: length is {len(key_material)} bytes. "
            f"Expected standard 158-byte key file, 32 raw bytes, or 64-character hex passkey."
        )
