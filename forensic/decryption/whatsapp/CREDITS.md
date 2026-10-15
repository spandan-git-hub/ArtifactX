# Credits & Attributions — WhatsApp Forensic Decryption

The WhatsApp decryption subsystem (`forensic/decryption/whatsapp/`) in ArtifactX is a clean, independent implementation designed strictly for non-destructive in-memory forensic analysis (master.md R4, R15).

## Consulted References & Documentation
- **wa-crypt-tools** (ElDavoo, GPLv3): Consulted strictly as a format specification reference and external test-time tool (`tools/groundtruth/crypto/wa_encrypt.py`, differential verification tests via subprocess).
- **WhatsApp Android Client Protocol & File Formats**: Documentation and structure notes recorded in `docs/FORMAT_NOTES.md`.
- **RFC 5869**: HMAC-based Extract-and-Expand Key Derivation Function (HKDF) for Crypt15 cipher key derivation.
- **NIST SP 800-38D**: Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (AES-GCM).

## Implementation Notice
- **Zero code copied**: This implementation is completely independent. No code from `wa-crypt-tools` or any GPL-licensed codebase has been copied or imported into `forensic/` or `backend/`.
- **Zero third-party protobuf dependency**: Includes an in-tree minimal varint and length-delimited protobuf wire parser (`protobuf_min.py`).
- **Cryptographic primitives**: Uses `cryptography` (Apache-2.0 / BSD) for AES-GCM and HKDF-SHA256.
