"""
Unified Forensic Decryption Orchestrator with plugin interface.
Legacy unvalidated decryptors have been unregistered per Section A6 / DEC-006.
Phase B6 will introduce independently validated decryptors adhering to Decryptor Protocol.
"""

from dataclasses import dataclass, field
import hashlib
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union, runtime_checkable

from forensic.decryption.detector import EncryptionDetector, FormatDetectionResult


@dataclass
class KeyMaterial:
    """Container for cryptographic key inputs without logging secrets."""
    raw_key: Optional[bytes] = None
    key_hex: Optional[str] = None
    key_file_bytes: Optional[bytes] = None
    key_type: str = "raw"


@dataclass
class DecryptionResult:
    """Result of a successful in-memory decryption operation."""
    plaintext: bytes
    format_id: str
    output_sha256: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Decryptor(Protocol):
    """Clean plugin interface for forensic decryption engines (A6.4)."""
    format_id: str

    def can_handle(self, header: bytes, filename: Optional[str] = None) -> bool:
        """Inspect header or filename to determine engine compatibility."""
        ...

    def decrypt(self, data: bytes, key_material: KeyMaterial) -> DecryptionResult:
        """Execute in-memory decryption with integrity checks."""
        ...


class DecryptorNotAvailableError(Exception):
    """Raised when no validated decryptor plugin is available for the requested format."""

    def __init__(self, format_name: str, message: Optional[str] = None):
        self.format_name = format_name
        super().__init__(
            message
            or f"Decryptor for format '{format_name}' is not available. "
            "Unvalidated decryptors were demoted pending Phase B6."
        )


class DecryptionOrchestrator:
    """
    Central coordinator for cryptographic forensic decryption plugins.
    Zero disk writes: operates strictly on in-memory buffers.
    """

    _registry: Dict[str, Decryptor] = {}

    @classmethod
    def register(cls, decryptor: Decryptor) -> None:
        """Register a validated decryptor engine plugin."""
        cls._registry[decryptor.format_id.lower()] = decryptor

    @classmethod
    def unregister(cls, format_id: str) -> None:
        """Unregister a decryptor engine plugin."""
        cls._registry.pop(format_id.lower(), None)

    @classmethod
    def get_registered_formats(cls) -> List[str]:
        """Return list of currently registered format IDs."""
        return list(cls._registry.keys())

    @classmethod
    def detect_format(cls, data: bytes, filename: Optional[str] = None) -> FormatDetectionResult:
        """Detect container encryption format, entropy, and parameters."""
        return EncryptionDetector.detect(data, filename)

    @classmethod
    def decrypt(
        cls,
        data: bytes,
        key_or_passcode: Union[str, bytes, KeyMaterial],
        format_hint: Optional[str] = None,
        filename: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Execute decryption workflow via registered plugins.
        Raises DecryptorNotAvailableError when no validated plugin is registered for format.
        """
        if not data:
            raise ValueError("Encrypted data buffer is empty.")

        params = parameters or {}

        # 1. Format resolution
        fmt = (format_hint or "").lower()
        if not fmt or fmt == "auto_detect":
            det = cls.detect_format(data, filename)
            if not det.is_encrypted or not det.format:
                raise ValueError(f"Could not automatically identify encryption format: {det.reasons}")
            fmt = det.format.lower()

        # 2. Lookup registered plugin
        decryptor = cls._registry.get(fmt)
        if decryptor is None:
            raise DecryptorNotAvailableError(format_name=fmt)

        # 3. Normalize key material
        if isinstance(key_or_passcode, KeyMaterial):
            km = key_or_passcode
        elif isinstance(key_or_passcode, bytes):
            km = KeyMaterial(raw_key=key_or_passcode, key_type="raw_bytes")
        elif isinstance(key_or_passcode, str):
            clean = key_or_passcode.strip()
            km = KeyMaterial(key_hex=clean, key_type="hex_string")
        else:
            raise ValueError("Invalid key material input type.")

        # 4. Execute decryption plugin
        input_sha256 = hashlib.sha256(data).hexdigest()
        result = decryptor.decrypt(data, km)

        output_sha256 = result.output_sha256 or hashlib.sha256(result.plaintext).hexdigest()
        provenance = {
            "format": result.format_id,
            "artifact_type": "decrypted_sqlite",
            "status": "SUCCEEDED",
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "size_bytes": len(result.plaintext),
            "parameters": {k: v for k, v in params.items() if "key" not in k.lower() and "pass" not in k.lower()},
            "operation_details": result.metadata,
        }

        return result.plaintext, provenance
