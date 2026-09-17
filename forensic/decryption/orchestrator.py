"""
Unified Forensic Decryption Orchestrator.
Dispatches encrypted payloads to the appropriate engine (WhatsApp Crypt12/14/15,
WhatsApp .enc media, Telegram SQLCipher, or Telegram MTProto) and returns verified
in-memory artifacts with complete judicial provenance.
"""

import hashlib
from typing import Any, Dict, Optional, Tuple, Union

from forensic.decryption.detector import EncryptionDetector, FormatDetectionResult
from forensic.decryption.whatsapp.crypt12 import Crypt12Decryptor
from forensic.decryption.whatsapp.crypt14 import Crypt14Decryptor
from forensic.decryption.whatsapp.crypt15 import Crypt15Decryptor
from forensic.decryption.whatsapp.key_parser import WhatsAppKey, WhatsAppKeyParser
from forensic.decryption.whatsapp.media import WhatsAppMediaDecryptor
from forensic.decryption.whatsapp.validator import SQLiteValidator
from forensic.decryption.telegram.sqlcipher import TelegramSQLCipherDecryptor, SQLCipherProfile
from forensic.decryption.telegram.mtproto import TelegramMTProtoDecryptor


class DecryptionOrchestrator:
    """Central coordinator for cryptographic forensic decryption."""

    @classmethod
    def detect_format(cls, data: bytes, filename: Optional[str] = None) -> FormatDetectionResult:
        """Detect container encryption format, entropy, and parameters."""
        return EncryptionDetector.detect(data, filename)

    @classmethod
    def decrypt(
        cls,
        data: bytes,
        key_or_passcode: Union[str, bytes, WhatsAppKey],
        format_hint: Optional[str] = None,
        filename: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Execute decryption workflow.
        Returns: (decrypted_bytes, provenance_metadata)
        """
        if not data:
            raise ValueError("Encrypted data buffer is empty.")

        params = parameters or {}

        # 1. Format resolution
        fmt = (format_hint or "").lower()
        if not fmt:
            det = cls.detect_format(data, filename)
            if not det.is_encrypted or not det.format:
                raise ValueError(f"Could not automatically identify encryption format: {det.reasons}")
            fmt = det.format

        input_sha256 = hashlib.sha256(data).hexdigest()

        # 2. Dispatch by format
        if fmt in ("crypt12", "whatsapp_crypt12"):
            wa_key = key_or_passcode if isinstance(key_or_passcode, WhatsAppKey) else WhatsAppKeyParser.parse(key_or_passcode)
            plain_bytes, meta = Crypt12Decryptor.decrypt(data, wa_key)
            artifact_type = "decrypted_sqlite"

        elif fmt in ("crypt14", "whatsapp_crypt14"):
            wa_key = key_or_passcode if isinstance(key_or_passcode, WhatsAppKey) else WhatsAppKeyParser.parse(key_or_passcode)
            plain_bytes, meta = Crypt14Decryptor.decrypt(data, wa_key)
            artifact_type = "decrypted_sqlite"

        elif fmt in ("crypt15", "whatsapp_crypt15"):
            plain_bytes, meta = Crypt15Decryptor.decrypt(
                data,
                key_or_passcode,
                iterations=params.get("iterations", Crypt15Decryptor.DEFAULT_ITERATIONS),
            )
            artifact_type = "decrypted_sqlite"

        elif fmt in ("enc", "whatsapp_enc", "media_enc"):
            media_type = params.get("media_type", "image")
            raw_media_key = key_or_passcode.cipher_key if isinstance(key_or_passcode, WhatsAppKey) else key_or_passcode
            plain_bytes, meta = WhatsAppMediaDecryptor.decrypt(data, raw_media_key, media_type)
            artifact_type = "decrypted_media"

        elif fmt in ("sqlcipher", "telegram_sqlcipher", "sqlcipher_v3", "sqlcipher_v4"):
            prof_name = "v3" if "v3" in fmt else params.get("profile", "v4")
            profile = SQLCipherProfile.get_profile(prof_name)
            if "page_size" in params:
                profile.page_size = int(params["page_size"])
            if "kdf_iterations" in params:
                profile.kdf_iterations = int(params["kdf_iterations"])

            plain_bytes, meta = TelegramSQLCipherDecryptor.decrypt(data, key_or_passcode, profile)
            artifact_type = "decrypted_sqlite"

        elif fmt in ("mtproto", "telegram_secret_chat", "enc_chat"):
            client_mode = params.get("client_mode", True)
            raw_auth_key = key_or_passcode.cipher_key if isinstance(key_or_passcode, WhatsAppKey) else key_or_passcode
            if isinstance(raw_auth_key, str):
                raw_auth_key = bytes.fromhex(raw_auth_key) if len(raw_auth_key) == 512 else raw_auth_key.encode("utf-8")
            plain_bytes, meta = TelegramMTProtoDecryptor.decrypt(data, raw_auth_key, client_mode)
            artifact_type = "recovered_secret_chat"

        else:
            raise ValueError(f"Unsupported decryption format: '{fmt}'.")

        # Judicial provenance summary
        output_sha256 = hashlib.sha256(plain_bytes).hexdigest()
        provenance = {
            "format": fmt,
            "artifact_type": artifact_type,
            "status": "SUCCEEDED",
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "size_bytes": len(plain_bytes),
            "parameters": {k: v for k, v in params.items() if "key" not in k.lower() and "pass" not in k.lower()},
            "operation_details": meta,
        }

        return plain_bytes, provenance
