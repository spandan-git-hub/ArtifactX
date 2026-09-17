"""
WhatsApp Encrypted Media (.enc) Decryption Engine.
Implements RFC 5869 HKDF key derivation, AES-256-CBC decryption,
HMAC-SHA256 authentication tag validation, and file-type magic detection.
Zero disk writes: outputs directly into in-memory buffers.
"""

import binascii
import hashlib
from typing import Dict, Optional, Tuple, Union
from cryptography.hazmat.primitives import hashes, hmac, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class WhatsAppMediaDecryptor:
    """Decryptor for WhatsApp .enc media attachments."""

    MEDIA_INFO_STRINGS = {
        "image": b"WhatsApp Image Keys",
        "audio": b"WhatsApp Audio Keys",
        "video": b"WhatsApp Video Keys",
        "document": b"WhatsApp Document Keys",
    }

    MAGIC_MIME_MAP = {
        b"\xff\xd8\xff": "image/jpeg",
        b"\x89PNG\r\n\x1a\n": "image/png",
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
        b"RIFF": "audio/wav",
        b"OggS": "audio/ogg",
        b"%PDF": "application/pdf",
        b"\x1a\x45\xdf\xa3": "video/webm",
    }

    @classmethod
    def expand_key(cls, media_key: bytes, media_type: str = "image") -> Tuple[bytes, bytes, bytes, bytes]:
        """
        Derive 112 bytes of key material using RFC 5869 HKDF-SHA256.
        Returns: (iv, cipher_key, mac_key, ref_key)
        """
        info = cls.MEDIA_INFO_STRINGS.get(media_type.lower(), b"WhatsApp Image Keys")
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=112,
            salt=b"\x00" * 32,
            info=info,
        )
        keys = hkdf.derive(media_key)
        iv = keys[0:16]
        cipher_key = keys[16:48]
        mac_key = keys[48:80]
        ref_key = keys[80:112]
        return iv, cipher_key, mac_key, ref_key

    @classmethod
    def detect_mime(cls, data: bytes) -> str:
        """Infer MIME type from decrypted file header magic."""
        if not data or len(data) < 4:
            return "application/octet-stream"

        for magic, mime in cls.MAGIC_MIME_MAP.items():
            if data.startswith(magic):
                return mime

        # MP4 detection
        if len(data) >= 12 and b"ftyp" in data[4:12]:
            return "video/mp4"

        return "application/octet-stream"

    @classmethod
    def decrypt(
        cls,
        encrypted_data: bytes,
        media_key: Union[bytes, str],
        media_type: str = "image",
    ) -> Tuple[bytes, Dict]:
        """
        Decrypt WhatsApp .enc media payload with HMAC-SHA256 authentication verification.
        Returns: (plaintext_media_bytes, operation_provenance_metadata)
        """
        # Minimum size: 16 bytes ciphertext + 10 bytes MAC = 26 bytes
        if len(encrypted_data) < 26:
            raise ValueError(f"Encrypted media file too small ({len(encrypted_data)} bytes).")

        # Parse media key
        if isinstance(media_key, str):
            clean = media_key.strip().replace(" ", "")
            if len(clean) == 64:
                raw_key = binascii.unhexlify(clean)
            else:
                try:
                    import base64
                    raw_key = base64.b64decode(clean)
                except Exception:
                    raw_key = clean.encode("utf-8")
        else:
            raw_key = bytes(media_key)

        if len(raw_key) != 32:
            raise ValueError(f"Media key must be exactly 32 bytes (got {len(raw_key)} bytes).")

        input_sha256 = hashlib.sha256(encrypted_data).hexdigest()

        # 1. Separate ciphertext and trailing 10-byte MAC
        ciphertext = encrypted_data[:-10]
        provided_mac = encrypted_data[-10:]

        # 2. Derive keys via HKDF (RFC 5869)
        iv, cipher_key, mac_key, _ = cls.expand_key(raw_key, media_type)

        # 3. Verify HMAC-SHA256
        h = hmac.HMAC(mac_key, hashes.SHA256())
        h.update(iv + ciphertext)
        computed_mac = h.finalize()[:10]

        if computed_mac != provided_mac:
            raise ValueError("Media HMAC-SHA256 authentication check failed (altered tag or wrong media key).")

        # 4. Decrypt AES-256-CBC
        cipher = Cipher(algorithms.AES(cipher_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        try:
            padded_plain = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            plaintext_bytes = unpadder.update(padded_plain) + unpadder.finalize()
        except Exception as e:
            raise ValueError(f"AES-256-CBC decryption or PKCS#7 unpadding failed: {str(e)}")

        output_sha256 = hashlib.sha256(plaintext_bytes).hexdigest()
        mime_type = cls.detect_mime(plaintext_bytes)

        metadata = {
            "format": "whatsapp_enc",
            "media_type": media_type,
            "cipher": "AES-256-CBC",
            "kdf": "HKDF-SHA256-RFC5869",
            "mac_verified": True,
            "mime_type": mime_type,
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "size_bytes": len(plaintext_bytes),
        }

        return plaintext_bytes, metadata

    @classmethod
    def create_fixture(
        cls,
        media_bytes: bytes,
        media_key: bytes,
        media_type: str = "image",
    ) -> bytes:
        """Synthetic fixture generator for WhatsApp .enc media."""
        iv, cipher_key, mac_key, _ = cls.expand_key(media_key, media_type)

        padder = padding.PKCS7(128).padder()
        padded = padder.update(media_bytes) + padder.finalize()

        cipher = Cipher(algorithms.AES(cipher_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        h = hmac.HMAC(mac_key, hashes.SHA256())
        h.update(iv + ciphertext)
        tag = h.finalize()[:10]

        return ciphertext + tag
