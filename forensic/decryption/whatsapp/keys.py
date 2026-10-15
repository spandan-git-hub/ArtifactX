"""
Cryptographic key material parsing and derivation for WhatsApp decryptors.
Strictly adheres to:
- master.md R5: Keys are radioactive. Redacted strings, no pickle, zeroing, no logging.
- master.md R12: Untrusted input hardening.
- master.md R15: Zero GPL code, independent implementation.
- DEC-002: Offline passphrase derivation is rejected with PassphraseNotSupported.
"""

from __future__ import annotations

import binascii
import struct
from typing import Optional, Tuple, Union

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from forensic.decryption.whatsapp.errors import (
    KeyInvalidFormat,
    KeyRequired,
    PassphraseNotSupported,
)
from forensic.decryption.whatsapp.types import KeyMaterial


def parse_java_byte_array(data: bytes) -> bytes:
    """
    Parse a Java-serialized byte array (byte[]) without third-party dependencies.
    Expected envelope (27 bytes header + N bytes payload):
    - Magic: 0xACED0005 (4B)
    - TC_ARRAY: 0x75 (1B)
    - TC_CLASSDESC: 0x72 (1B)
    - Name length: 0x0002 (2B)
    - Name: b"[B" (2B)
    - SerialVersionUID: 8B
    - ClassDescFlags: 1B
    - Field count: 0x0000 (2B)
    - TC_ENDBLOCKDATA: 0x78 (1B)
    - TC_NULL (superclass): 0x70 (1B)
    - Array length: 4B big-endian integer N
    - Payload: N bytes
    """
    if len(data) < 27:
        raise KeyInvalidFormat("Key file is too small to be a valid Java-serialized byte array.")

    magic, tc_arr, tc_desc = struct.unpack(">IBB", data[:6])
    if magic != 0xACED0005 or tc_arr != 0x75 or tc_desc != 0x72:
        raise KeyInvalidFormat("Key file does not contain a valid Java serialized object header.")

    name_len = struct.unpack(">H", data[6:8])[0]
    if name_len != 2 or data[8:10] != b"[B":
        raise KeyInvalidFormat("Serialized Java object is not a byte array ([B).")

    # Skip 8B UID + 1B flags + 2B fields (0) + 1B endblock (0x78) + 1B null (0x70) -> 13 bytes
    array_len_offset = 10 + 8 + 1 + 2 + 1 + 1
    if len(data) < array_len_offset + 4:
        raise KeyInvalidFormat("Java serialized stream truncated before array length.")

    arr_len = struct.unpack(">I", data[array_len_offset : array_len_offset + 4])[0]
    payload_start = array_len_offset + 4
    payload_end = payload_start + arr_len

    if len(data) != payload_end:
        raise KeyInvalidFormat(
            f"Java serialized byte array length mismatch: declared {arr_len} bytes, "
            f"total data len is {len(data)}, expected {payload_end} bytes."
        )

    return data[payload_start:payload_end]


class WhatsAppKeyParser:
    """
    Parses and derives forensic key material for crypt14 and crypt15 containers.
    Never logs or echoes raw key bytes.
    """

    @classmethod
    def parse_crypt14_key(cls, key_input: Union[bytes, str, KeyMaterial, None]) -> KeyMaterial:
        """
        Parse Crypt14 key material:
        - Java-serialized key file (158 bytes)
        - Raw 131-byte array
        - Raw 32-byte key
        - 64-hex character string
        """
        if key_input is None:
            raise KeyRequired("Crypt14 decryption requires key material (key file or 32-byte key).")

        if isinstance(key_input, KeyMaterial):
            key_bytes = key_input.raw_key
        elif isinstance(key_input, str):
            clean = key_input.strip()
            if not clean:
                raise KeyInvalidFormat("Crypt14 key input string is empty.")
            # Check if hex string
            try:
                key_bytes = bytes.fromhex(clean)
            except ValueError:
                raise KeyInvalidFormat("Crypt14 key string is not valid hexadecimal.")
        elif isinstance(key_input, (bytes, bytearray)):
            key_bytes = bytes(key_input)
        else:
            raise KeyInvalidFormat(f"Unsupported key input type: {type(key_input).__name__}")

        if not key_bytes:
            raise KeyInvalidFormat("Crypt14 key material is empty.")

        # Check if Java serialized object (158 bytes or starts with ACED0005)
        if key_bytes.startswith(b"\xac\xed\x00\x05"):
            raw_payload = parse_java_byte_array(key_bytes)
            if len(raw_payload) == 131:
                # 32-byte AES key is at offset 99..131
                aes_key = raw_payload[99:131]
            elif len(raw_payload) == 32:
                aes_key = raw_payload
            else:
                raise KeyInvalidFormat(f"Java byte array payload length {len(raw_payload)} is invalid for crypt14.")
        elif len(key_bytes) == 131:
            aes_key = key_bytes[99:131]
        elif len(key_bytes) == 32:
            aes_key = key_bytes
        else:
            raise KeyInvalidFormat(
                f"Crypt14 key material length {len(key_bytes)} is invalid; expected 158, 131, or 32 bytes."
            )

        if len(aes_key) != 32:
            raise KeyInvalidFormat(f"Derived Crypt14 AES key length {len(aes_key)} != 32.")

        return KeyMaterial(raw_key=aes_key, key_type="crypt14")

    @classmethod
    def parse_crypt15_key(cls, key_input: Union[bytes, str, KeyMaterial, None]) -> Tuple[KeyMaterial, KeyMaterial]:
        """
        Parse Crypt15 key material and derive AES cipher key:
        Returns: (root_key_material, cipher_key_material)
        Inputs accepted:
        - 64-hex character string
        - binary encrypted_backup.key (59 bytes Java-serialized or raw 32-byte root key)
        - raw 32-byte root key
        Passphrases are rejected per DEC-002 with PassphraseNotSupported.
        """
        if key_input is None:
            raise KeyRequired("Crypt15 decryption requires key material (64-hex key or encrypted_backup.key).")

        if isinstance(key_input, KeyMaterial):
            key_bytes = key_input.raw_key
            if len(key_bytes) not in (32, 59):
                try:
                    cand = key_bytes.decode("utf-8").strip()
                    if len(cand) == 64 and all(c in "0123456789abcdefABCDEF" for c in cand):
                        key_bytes = bytes.fromhex(cand)
                    else:
                        raise PassphraseNotSupported()
                except UnicodeDecodeError:
                    raise KeyInvalidFormat(f"Crypt15 key material length {len(key_bytes)} is invalid; expected 59 or 32 bytes.")
        elif isinstance(key_input, str):
            clean = key_input.strip()
            if not clean:
                raise KeyInvalidFormat("Crypt15 key input string is empty.")

            # Check if this looks like a password/passphrase rather than 64-hex key
            if len(clean) != 64 or not all(c in "0123456789abcdefABCDEF" for c in clean):
                # If it's not a 64-character hex string, check if it's a passphrase attempt
                if len(clean) < 64 or not all(c in "0123456789abcdefABCDEF" for c in clean):
                    raise PassphraseNotSupported()

            try:
                key_bytes = bytes.fromhex(clean)
            except ValueError:
                raise PassphraseNotSupported()
        elif isinstance(key_input, (bytes, bytearray)):
            key_bytes = bytes(key_input)
        else:
            raise KeyInvalidFormat(f"Unsupported key input type: {type(key_input).__name__}")

        if not key_bytes:
            raise KeyInvalidFormat("Crypt15 key material is empty.")

        # Check if Java serialized object (59 bytes or starts with ACED0005)
        if key_bytes.startswith(b"\xac\xed\x00\x05"):
            raw_payload = parse_java_byte_array(key_bytes)
            if len(raw_payload) == 32:
                root_key = raw_payload
            else:
                raise KeyInvalidFormat(f"Java byte array payload length {len(raw_payload)} is invalid for crypt15.")
        elif len(key_bytes) == 32:
            root_key = key_bytes
        else:
            raise KeyInvalidFormat(
                f"Crypt15 key material length {len(key_bytes)} is invalid; expected 59 or 32 bytes."
            )

        # Derive AES-256-GCM cipher key via HKDF-SHA256
        # Salt: 32 zero bytes
        # Info: b"backup encryption"
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"\x00" * 32,
            info=b"backup encryption",
        )
        cipher_key = hkdf.derive(root_key)

        root_km = KeyMaterial(raw_key=root_key, key_type="crypt15_root")
        cipher_km = KeyMaterial(raw_key=cipher_key, key_type="crypt15_cipher")
        return root_km, cipher_km
