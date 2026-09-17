# R3 — Database and Media Decryption Subsystem

## Objective

Add controlled, auditable support for encrypted WhatsApp and Telegram artifacts described in the supplied specification.

## Critical qualification

The source document contains protocol assumptions, byte offsets, cryptographic modes, and KDF parameters. These must be verified against authoritative format documentation and controlled forensic fixtures before implementation is treated as production-correct. Do not blindly encode an example as universal truth.

## Architecture

```text
Encrypted evidence
      |
      v
Format detector
      |
      +--> WhatsApp DB decryptor
      |      +--> Crypt12
      |      +--> Crypt14
      |      +--> Crypt15
      |
      +--> WhatsApp media decryptor
      |
      +--> Telegram SQLCipher handler
      |
      +--> Telegram secret-chat handler
      |
      v
Verified derived artifact
      |
      v
Existing forensic parser
```

## 1. Format detection

Create:
`forensic/decryption/detector.py`

Detect by:
- filename;
- magic/header;
- entropy/structure;
- cryptographic validation.

Never identify encryption solely from a filename.

## 2. WhatsApp database decryption

Create:
`forensic/decryption/whatsapp/`

Modules:
- `key_parser.py`
- `crypt12.py`
- `crypt14.py`
- `crypt15.py`
- `validator.py`

Inputs must be:
- encrypted evidence blob;
- authorized key/passkey material;
- format parameters.

Outputs:
- in-memory plaintext SQLite bytes;
- SHA-256;
- decryption operation metadata.

Do not persist plaintext to local disk.

## 3. WhatsApp media

Create:
`forensic/decryption/whatsapp/media.py`

Use the source specification's HKDF-based design as an implementation hypothesis. Verify:
- media-key source;
- info strings;
- key expansion;
- MAC construction;
- ciphertext layout;
- padding;
- file-type validation.

Output decrypted bytes directly to the media artifact pipeline.

## 4. Telegram SQLCipher

Create:
`forensic/decryption/telegram/sqlcipher.py`

Support:
- encrypted-header detection;
- authorized passcode input;
- verified parameter profiles;
- plaintext export to memory;
- SQLite integrity validation.

Do not log passcodes.

If a password dictionary/testing mode is implemented for authorized forensic validation, require an explicit examiner action, enforce bounded attempts/rate limits, and log only the operation metadata—not secrets.

## 5. Telegram secret chats

Create:
`forensic/decryption/telegram/mtproto.py`

Treat MTProto parameters and KDF formulas as version-sensitive. Validate against known-good fixtures before production use.

Outputs must include:
- recovered plaintext;
- source encrypted payload hash;
- key/operation provenance without exposing secret material;
- protocol/version metadata.

## 6. Derived-artifact provenance

For every successful decryption record:
- parent evidence file ID;
- parent SHA-256;
- method;
- format/version;
- parameter profile;
- output SHA-256;
- byte length;
- examiner/operator;
- timestamp;
- validation status.

## 7. API

Suggested:
- `POST /api/evidence/{evidence_id}/decryption/detect`
- `POST /api/evidence/{evidence_id}/decryption/run`
- `GET /api/evidence/{evidence_id}/decryption/operations`
- `GET /api/evidence/{evidence_id}/derived-artifacts`

## 8. Tests

Fixtures must cover:
- valid/invalid keys;
- corrupted ciphertext;
- wrong passcode;
- truncated input;
- altered authentication tag;
- valid plaintext database handoff;
- valid media output;
- zero local disk writes.

Never ship real seized keys, passcodes, or private evidence in tests.
