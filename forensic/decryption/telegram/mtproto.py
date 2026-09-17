"""
Telegram MTProto Secret Chat Decryption Engine.
Implements MTProto v2 AES-256-IGE key derivation and block decryption
for seized end-to-end encrypted Telegram secret chats (enc_chats).
"""

import hashlib
import struct
from typing import Dict, Optional, Tuple, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class TelegramMTProtoDecryptor:
    """Decryptor for Telegram MTProto v2 Secret Chat payloads."""

    @classmethod
    def derive_keys(
        cls,
        auth_key: bytes,
        msg_key: bytes,
        client_mode: bool = True,
    ) -> Tuple[bytes, bytes]:
        """
        Derive AES-256-IGE key and 32-byte IV from 256-byte auth_key and 16-byte msg_key.
        Formula (MTProto v2.0):
        x = 0 for client, 8 for server
        sha256_a = SHA256(msg_key + auth_key[x : x + 36])
        sha256_b = SHA256(auth_key[x + 40 : x + 76] + msg_key)
        aes_key = sha256_a[0:8] + sha256_b[8:24] + sha256_a[24:32]
        aes_iv = sha256_b[0:8] + sha256_a[8:24] + sha256_b[24:32]
        """
        if len(auth_key) < 128:
            raise ValueError(f"Auth key too short ({len(auth_key)} bytes; expected 256 bytes).")
        if len(msg_key) != 16:
            raise ValueError(f"Message key must be exactly 16 bytes (got {len(msg_key)} bytes).")

        x = 0 if client_mode else 8
        sha256_a = hashlib.sha256(msg_key + auth_key[x : x + 36]).digest()
        sha256_b = hashlib.sha256(auth_key[x + 40 : x + 76] + msg_key).digest()

        aes_key = sha256_a[0:8] + sha256_b[8:24] + sha256_a[24:32]
        aes_iv = sha256_b[0:8] + sha256_a[8:24] + sha256_b[24:32]
        return aes_key, aes_iv

    @classmethod
    def ige_decrypt(cls, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """
        Decrypt ciphertext using AES-256 in Infinite Garble Extension (IGE) mode.
        """
        if len(ciphertext) % 16 != 0:
            raise ValueError("Ciphertext length must be a multiple of 16 for AES-IGE mode.")
        if len(key) != 32 or len(iv) != 32:
            raise ValueError("AES-IGE requires a 32-byte key and 32-byte IV.")

        cipher = Cipher(algorithms.AES(key), modes.ECB())
        decryptor = cipher.decryptor()
        iv1, iv2 = iv[:16], iv[16:32]
        c_prev, p_prev = iv1, iv2

        plaintext = bytearray()
        for i in range(0, len(ciphertext), 16):
            c_block = ciphertext[i : i + 16]
            x = bytes(a ^ b for a, b in zip(c_block, p_prev))
            dec_block = decryptor.update(x)
            p_block = bytes(a ^ b for a, b in zip(dec_block, c_prev))
            plaintext.extend(p_block)
            c_prev = c_block
            p_prev = p_block

        return bytes(plaintext)

    @classmethod
    def ige_encrypt(cls, plaintext: bytes, key: bytes, iv: bytes) -> bytes:
        """
        Encrypt plaintext using AES-256 in Infinite Garble Extension (IGE) mode.
        """
        if len(plaintext) % 16 != 0:
            # Pad to 16 bytes
            pad_len = 16 - (len(plaintext) % 16)
            plaintext += b"\x00" * pad_len

        cipher = Cipher(algorithms.AES(key), modes.ECB())
        encryptor = cipher.encryptor()
        iv1, iv2 = iv[:16], iv[16:32]
        c_prev, p_prev = iv1, iv2

        ciphertext = bytearray()
        for i in range(0, len(plaintext), 16):
            p_block = plaintext[i : i + 16]
            x = bytes(a ^ b for a, b in zip(p_block, c_prev))
            enc_block = encryptor.update(x)
            c_block = bytes(a ^ b for a, b in zip(enc_block, p_prev))
            ciphertext.extend(c_block)
            c_prev = c_block
            p_prev = p_block

        return bytes(ciphertext)

    @classmethod
    def decrypt(
        cls,
        encrypted_payload: bytes,
        auth_key: bytes,
        client_mode: bool = True,
    ) -> Tuple[bytes, Dict]:
        """
        Decrypt a serialized MTProto secret chat container.
        Payload layout:
        - Bytes 0..8: auth_key_id (64-bit key fingerprint)
        - Bytes 8..24: msg_key (16 bytes)
        - Bytes 24..end: encrypted ciphertext (multiple of 16)
        """
        if len(encrypted_payload) < 40:
            raise ValueError(f"MTProto payload too short ({len(encrypted_payload)} bytes).")

        auth_key_id = encrypted_payload[:8]
        msg_key = encrypted_payload[8:24]
        ciphertext = encrypted_payload[24:]

        if len(ciphertext) % 16 != 0:
            raise ValueError("MTProto ciphertext length must be a multiple of 16.")

        input_sha256 = hashlib.sha256(encrypted_payload).hexdigest()

        # Derive keys
        aes_key, aes_iv = cls.derive_keys(auth_key, msg_key, client_mode)

        # Decrypt IGE
        decrypted_raw = cls.ige_decrypt(ciphertext, aes_key, aes_iv)

        # Verify msg_key (MTProto v2: first 16 bytes of SHA256(auth_key[88..120] + decrypted_raw))
        expected_msg_key = hashlib.sha256(auth_key[88:120] + decrypted_raw).digest()[:16]
        msg_key_verified = (msg_key == expected_msg_key)

        output_sha256 = hashlib.sha256(decrypted_raw).hexdigest()

        metadata = {
            "format": "mtproto",
            "cipher": "AES-256-IGE",
            "auth_key_id": auth_key_id.hex(),
            "msg_key_verified": msg_key_verified,
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "size_bytes": len(decrypted_raw),
        }

        return decrypted_raw, metadata

    @classmethod
    def create_fixture(
        cls,
        message_bytes: bytes,
        auth_key: bytes,
        client_mode: bool = True,
    ) -> bytes:
        """Synthetic fixture generator for MTProto secret chat payload."""
        # Pad message to 16 bytes
        if len(message_bytes) % 16 != 0:
            message_bytes += b"\x00" * (16 - (len(message_bytes) % 16))

        # MTProto v2: msg_key = SHA256(auth_key[88..120] + message_bytes)[:16]
        msg_key = hashlib.sha256(auth_key[88:120] + message_bytes).digest()[:16]
        auth_key_id = hashlib.sha1(auth_key).digest()[-8:]

        aes_key, aes_iv = cls.derive_keys(auth_key, msg_key, client_mode)
        ciphertext = cls.ige_encrypt(message_bytes, aes_key, aes_iv)

        return auth_key_id + msg_key + ciphertext
