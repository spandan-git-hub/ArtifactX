"""
ArtifactX Phase E: R3 Database and Media Decryption Validation Suite.

Validates:
1. Encryption format and entropy detection (heuristics, not solely extensions)
2. WhatsApp Key file (158-byte) parsing, 64-hex passkey parsing, and secret redaction
3. WhatsApp Crypt12 synthetic fixture decryption & in-memory SQLite validation
4. WhatsApp Crypt14 synthetic fixture decryption & PBKDF2 derivation
5. WhatsApp Crypt15 synthetic fixture decryption & SHA512 derivation
6. WhatsApp Media (.enc) RFC 5869 HKDF key expansion, AES-CBC & HMAC verification
7. Telegram SQLCipher page-by-page decryption, parameter profiles, & PIN tester
8. Telegram MTProto Secret Chat AES-256-IGE mode decryption
9. Negative testing: Wrong key, wrong passcode, altered MAC, and corrupted ciphertext
10. End-to-End API execution, DerivedArtifact BYTEA storage, and Zero-Local-Disk verification
"""

import binascii
import hashlib
import io
import os
from pathlib import Path
import sqlite3
import struct
import zlib
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.models.models import (
    Case,
    Evidence,
    DerivedArtifact,
    DecryptionOperation,
    ActivityLog,
)
from forensic.decryption import (
    EncryptionDetector,
    FormatDetectionResult,
    DecryptionOrchestrator,
)
from forensic.decryption.whatsapp import (
    WhatsAppKeyParser,
    WhatsAppKey,
    SQLiteValidator,
    Crypt12Decryptor,
    Crypt14Decryptor,
    Crypt15Decryptor,
    WhatsAppMediaDecryptor,
)
from forensic.decryption.telegram import (
    TelegramSQLCipherDecryptor,
    SQLCipherProfile,
    TelegramMTProtoDecryptor,
)


def _make_sample_sqlite(reserve: int = 0) -> bytes:
    """Create a minimal in-memory SQLite database with tables and records."""
    con = sqlite3.connect(":memory:")
    if reserve > 0:
        db = bytearray(con.serialize())
        con.close()
        db[20] = reserve
        struct.pack_into(">H", db, 105, 4096 - reserve)
        con = sqlite3.connect(":memory:")
        con.deserialize(bytes(db))

    con.execute("CREATE TABLE messages (_id INTEGER PRIMARY KEY, key_remote_jid TEXT, data TEXT, timestamp INTEGER);")
    con.execute("INSERT INTO messages VALUES (1, '12345@s.whatsapp.net', 'Forensic exhibit text payload', 1700000000);")
    con.execute("CREATE TABLE contacts (jid TEXT PRIMARY KEY, display_name TEXT);")
    con.execute("INSERT INTO contacts VALUES ('12345@s.whatsapp.net', 'John Doe');")
    db_bytes = con.serialize()
    con.close()
    return db_bytes


def test_format_and_entropy_detector():
    print("\n--- [Test 1] Encryption Format and Entropy Detector ---")

    sqlite_plain = _make_sample_sqlite()
    det_plain = EncryptionDetector.detect(sqlite_plain, "msgstore.db")
    assert not det_plain.is_encrypted, "Plain SQLite should not be flagged as encrypted"
    assert det_plain.confidence == 1.0

    # High entropy random payload with .crypt12
    fake_crypt12 = b"\x00\x01" + b"ArtifactX_Crypt12_Header" + os.urandom(200)
    det12 = EncryptionDetector.detect(fake_crypt12, "msgstore.db.crypt12")
    assert det12.is_encrypted
    assert det12.format == "crypt12"
    assert det12.entropy > 7.0

    # SQLCipher candidate (4096-byte page alignment, high entropy, no sqlite magic)
    fake_sqlcipher = os.urandom(4096 * 2)
    det_sql = EncryptionDetector.detect(fake_sqlcipher, "cache4.db")
    assert det_sql.is_encrypted
    assert det_sql.format == "sqlcipher"
    assert det_sql.parameters.get("page_size") == 4096

    # WhatsApp .enc media (16-byte block alignment + 10-byte MAC)
    fake_enc = os.urandom(16 * 10) + os.urandom(10)
    det_enc = EncryptionDetector.detect(fake_enc, "photo.jpg.enc")
    assert det_enc.is_encrypted
    assert det_enc.format == "whatsapp_enc"

    print("  -> Unencrypted SQLite correctly identified as plaintext.")
    print("  -> Crypt12, SQLCipher, and WhatsApp .enc formats accurately detected via entropy and layout.")


def test_whatsapp_key_parser_and_redaction():
    print("\n--- [Test 2] WhatsApp Key Parser & Judicial Secret Redaction ---")

    # Construct synthetic 158-byte /files/key file
    # Bytes 0..2: magic, 30..62: 32-byte key, 110..126: 16-byte IV
    raw_aes_key = os.urandom(32)
    raw_iv = os.urandom(16)
    key_file = bytearray(158)
    key_file[0:3] = b"\x00\x01\x02"
    key_file[30:62] = raw_aes_key
    key_file[110:126] = raw_iv

    parsed_key = WhatsAppKeyParser.parse(bytes(key_file))
    assert parsed_key.cipher_key == raw_aes_key
    assert parsed_key.iv == raw_iv
    assert parsed_key.key_type == "CRYPT12_14_FILE"

    # Redaction test: raw key must never be visible in string representations
    repr_str = repr(parsed_key)
    str_str = str(parsed_key)
    assert "SECRET REDACTED" in repr_str
    assert binascii.hexlify(raw_aes_key).decode("ascii") not in repr_str
    assert binascii.hexlify(raw_aes_key).decode("ascii") not in str_str

    # Parse 64-hex passkey for Crypt15
    hex_passkey = binascii.hexlify(os.urandom(32)).decode("ascii")
    parsed_passkey = WhatsAppKeyParser.parse(hex_passkey)
    assert len(parsed_passkey.cipher_key) == 32
    assert parsed_passkey.key_type == "CRYPT15_PASSKEY"

    print("  -> 158-byte WhatsApp key structure and 64-hex passkey parsed accurately.")
    print("  -> Judicial secret redaction verified: raw keys masked in all representations.")


def test_crypt12_decryption():
    print("\n--- [Test 3] WhatsApp Crypt12 Decryption & Validation ---")

    sqlite_plain = _make_sample_sqlite()
    key = WhatsAppKey(cipher_key=os.urandom(32), iv=os.urandom(16))

    fixture = Crypt12Decryptor.create_fixture(sqlite_plain, key, compress=True)
    decrypted, meta = Crypt12Decryptor.decrypt(fixture, key)

    assert decrypted == sqlite_plain
    assert meta["format"] == "crypt12"
    assert meta["output_sha256"] == hashlib.sha256(sqlite_plain).hexdigest()
    assert meta["validation"]["valid"] is True
    assert "messages" in meta["validation"]["tables"]
    assert meta["validation"]["integrity_check"] == "ok"

    print("  -> Crypt12 AES-256-GCM decryption succeeded.")
    print("  -> In-memory SQLite integrity validated ('ok', 2 tables recovered).")


def test_crypt14_decryption():
    print("\n--- [Test 4] WhatsApp Crypt14 Decryption & PBKDF2 Key Derivation ---")

    sqlite_plain = _make_sample_sqlite()
    key = WhatsAppKey(cipher_key=os.urandom(32), iv=os.urandom(16))

    fixture = Crypt14Decryptor.create_fixture(sqlite_plain, key, compress=True)
    decrypted, meta = Crypt14Decryptor.decrypt(fixture, key)

    assert decrypted == sqlite_plain
    assert meta["format"] == "crypt14"
    assert meta["kdf"] == "PBKDF2-HMAC-SHA256"
    assert meta["output_sha256"] == hashlib.sha256(sqlite_plain).hexdigest()
    assert meta["validation"]["valid"] is True

    print("  -> Crypt14 PBKDF2-HMAC-SHA256 session key derivation succeeded.")
    print("  -> In-memory SQLite database validated successfully.")


def test_crypt15_decryption():
    print("\n--- [Test 5] WhatsApp Crypt15 64-Hex Passkey Decryption ---")

    sqlite_plain = _make_sample_sqlite()
    passkey_hex = binascii.hexlify(os.urandom(32)).decode("ascii")

    fixture = Crypt15Decryptor.create_fixture(sqlite_plain, passkey_hex, compress=True, iterations=1000)
    decrypted, meta = Crypt15Decryptor.decrypt(fixture, passkey_hex, iterations=1000)

    assert decrypted == sqlite_plain
    assert meta["format"] == "crypt15"
    assert meta["kdf"] == "PBKDF2-HMAC-SHA512"
    assert meta["output_sha256"] == hashlib.sha256(sqlite_plain).hexdigest()
    assert meta["validation"]["valid"] is True

    print("  -> Crypt15 64-hex passkey decryption with PBKDF2-HMAC-SHA512 verified.")


def test_whatsapp_media_hkdf_decryption():
    print("\n--- [Test 6] WhatsApp Media (.enc) HKDF RFC 5869 Decryption ---")

    # Test JPEG image
    sample_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + os.urandom(500)
    media_key = os.urandom(32)

    fixture = WhatsAppMediaDecryptor.create_fixture(sample_jpeg, media_key, media_type="image")
    decrypted, meta = WhatsAppMediaDecryptor.decrypt(fixture, media_key, media_type="image")

    assert decrypted == sample_jpeg
    assert meta["format"] == "whatsapp_enc"
    assert meta["mime_type"] == "image/jpeg"
    assert meta["mac_verified"] is True
    assert meta["output_sha256"] == hashlib.sha256(sample_jpeg).hexdigest()

    # Test PDF document
    sample_pdf = b"%PDF-1.4\n%ArtifactX Forensic Exhibit\n" + os.urandom(300)
    doc_fixture = WhatsAppMediaDecryptor.create_fixture(sample_pdf, media_key, media_type="document")
    doc_decrypted, doc_meta = WhatsAppMediaDecryptor.decrypt(doc_fixture, media_key, media_type="document")
    assert doc_decrypted == sample_pdf
    assert doc_meta["mime_type"] == "application/pdf"

    print("  -> WhatsApp .enc media decrypted using RFC 5869 HKDF key expansion.")
    print("  -> Trailing 10-byte HMAC-SHA256 authentication verified intact.")
    print("  -> File MIME signatures (JPEG, PDF) successfully recognized.")


def test_telegram_sqlcipher_decryption():
    print("\n--- [Test 7] Telegram SQLCipher Decryption & Passcode Verification ---")

    sqlite_plain = _make_sample_sqlite(reserve=48)
    passcode = "ForensicPasscode42"

    prof = SQLCipherProfile(
        name="v4_test",
        page_size=4096,
        kdf_algorithm="SHA256",
        kdf_iterations=1000,
        reserve_size=48,
        hmac_algorithm="SHA256",
    )

    fixture = TelegramSQLCipherDecryptor.create_fixture(sqlite_plain, passcode, profile=prof)

    # 1. Test passcode checker
    assert TelegramSQLCipherDecryptor.test_passcode(fixture, passcode, profile=prof) is True
    assert TelegramSQLCipherDecryptor.test_passcode(fixture, "WrongPasscode99", profile=prof) is False

    # 2. Test authorized PIN brute force / dictionary tester
    candidates = ["0000", "1234", "ForensicPasscode42", "9999"]
    found_pin = TelegramSQLCipherDecryptor.authorized_pin_brute_force(fixture, candidates, profile=prof)
    assert found_pin == passcode

    # 3. Full page-by-page decryption
    decrypted, meta = TelegramSQLCipherDecryptor.decrypt(fixture, passcode, profile=prof)
    assert meta["format"] == "sqlcipher"
    assert meta["pages_decrypted"] >= 1
    assert meta["validation"]["valid"] is True
    assert "messages" in meta["validation"]["tables"]

    print("  -> SQLCipher Page 1 HMAC & salt verification passed.")
    print("  -> Authorized passcode tester and dictionary tester validated.")
    print("  -> Pure-Python page-by-page AES-256-CBC decryption yielded valid SQLite database.")


def test_telegram_mtproto_decryption():
    print("\n--- [Test 8] Telegram MTProto Secret Chat AES-256-IGE Decryption ---")

    auth_key = os.urandom(256)
    message_payload = b"Top secret operational communication coordinates: 52.5200, 13.4050"

    fixture = TelegramMTProtoDecryptor.create_fixture(message_payload, auth_key, client_mode=True)
    decrypted, meta = TelegramMTProtoDecryptor.decrypt(fixture, auth_key, client_mode=True)

    assert message_payload in decrypted
    assert meta["format"] == "mtproto"
    assert meta["cipher"] == "AES-256-IGE"
    assert meta["msg_key_verified"] is True

    print("  -> Telegram MTProto v2 AES-256-IGE block decryption verified.")
    print("  -> msg_key fingerprint and plaintext secret payload recovered.")


def test_negative_security_and_authenticity():
    print("\n--- [Test 9] Negative Security Tests: Wrong Keys & Tampering ---")

    sqlite_plain = _make_sample_sqlite()
    valid_key = WhatsAppKey(cipher_key=os.urandom(32), iv=os.urandom(16))
    wrong_key = WhatsAppKey(cipher_key=os.urandom(32), iv=os.urandom(16))

    fixture = Crypt12Decryptor.create_fixture(sqlite_plain, valid_key, compress=True)

    # 1. Wrong key
    try:
        Crypt12Decryptor.decrypt(fixture, wrong_key)
        assert False, "Decryption with wrong key must raise ValueError"
    except ValueError as e:
        assert "authentication failed" in str(e).lower() or "corrupted" in str(e).lower()

    # 2. Tampered ciphertext
    tampered = bytearray(fixture)
    tampered[-5] ^= 0xFF  # Flip bit in GCM tag
    try:
        Crypt12Decryptor.decrypt(bytes(tampered), valid_key)
        assert False, "Decryption of altered ciphertext must raise ValueError"
    except ValueError as e:
        assert "authentication failed" in str(e).lower()

    # 3. Altered media MAC
    media_key = os.urandom(32)
    enc_media = bytearray(WhatsAppMediaDecryptor.create_fixture(b"image_bytes", media_key))
    enc_media[-1] ^= 0x01  # Alter MAC trailer
    try:
        WhatsAppMediaDecryptor.decrypt(bytes(enc_media), media_key)
        assert False, "Media with altered HMAC must raise ValueError"
    except ValueError as e:
        assert "authentication check failed" in str(e).lower()

    print("  -> Wrong key rejection confirmed.")
    print("  -> GCM authentication tag tampering detected and rejected.")
    print("  -> Altered media HMAC-SHA256 signature detected and rejected.")


def test_e2e_api_and_zero_disk_storage():
    print("\n--- [Test 10] End-to-End Decryption API & Zero-Local-Disk Invariant ---")

    uploads_dir = Path("uploads")
    reports_dir = Path("reports")
    initial_uploads = list(uploads_dir.glob("*")) if uploads_dir.exists() else []
    initial_reports = list(reports_dir.glob("*")) if reports_dir.exists() else []
    assert len(initial_uploads) == 0, f"uploads/ not clean: {initial_uploads}"
    assert len(initial_reports) == 0, f"reports/ not clean: {initial_reports}"

    client = TestClient(app)

    # 1. Create a test case
    case_res = client.post("/api/cases/", json={
        "name": "Phase E R3 Decryption Test Case",
        "description": "Validation of cryptographic decryption pipeline and derived exhibits",
        "investigator": "Forensic Specialist",
    })
    assert case_res.status_code == 200
    case_id = case_res.json()["id"]
    print(f"  -> Created Case ID: {case_id}")

    db = SessionLocal()
    try:
        # 2. Upload synthetic Crypt12 evidence directly into PostgreSQL BYTEA
        sqlite_plain = _make_sample_sqlite()
        wa_key = WhatsAppKey(cipher_key=os.urandom(32), iv=os.urandom(16))
        crypt12_fixture = Crypt12Decryptor.create_fixture(sqlite_plain, wa_key, compress=True)
        crypt12_hash = hashlib.sha256(crypt12_fixture).hexdigest()

        evidence = Evidence(
            case_id=case_id,
            original_filename="msgstore.db.crypt12",
            storage_path="",  # Zero disk path
            sha256=crypt12_hash,
            content_type="application/octet-stream",
            evidence_type="WHATSAPP_ENCRYPTED",
            content_bytes=crypt12_fixture,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        print(f"  -> Uploaded Encrypted Evidence ID: {evidence.id} (PostgreSQL BYTEA)")

        # 3. Test Detection API
        det_res = client.post(f"/api/evidence/{evidence.id}/decryption/detect")
        assert det_res.status_code == 200
        det_data = det_res.json()
        assert det_data["is_encrypted"] is True
        assert det_data["format"] == "crypt12"
        print(f"  -> Detection API confirmed: format={det_data['format']}, entropy={det_data['entropy']:.2f}")

        # 4. Test Decryption Run API
        key_hex = binascii.hexlify(wa_key.cipher_key).decode("ascii")
        run_res = client.post(f"/api/evidence/{evidence.id}/decryption/run", json={
            "key_material": key_hex,
            "format_override": "crypt12",
        })
        assert run_res.status_code == 200
        run_data = run_res.json()
        assert run_data["status"] == "SUCCEEDED"
        assert run_data["output_sha256"] == hashlib.sha256(sqlite_plain).hexdigest()
        derived_id = run_data["derived_artifact_id"]
        assert derived_id is not None
        print(f"  -> Decryption Run API SUCCEEDED! Derived Artifact ID: {derived_id}")

        # 5. Verify Derived Artifact in Database
        derived = db.query(DerivedArtifact).filter(DerivedArtifact.id == derived_id).first()
        assert derived is not None
        assert derived.artifact_type == "decrypted_sqlite"
        assert derived.content_bytes == sqlite_plain
        assert derived.sha256 == hashlib.sha256(sqlite_plain).hexdigest()
        print(f"  -> Derived exhibit verified in PostgreSQL BYTEA ({len(derived.content_bytes)} bytes)")

        # 6. Test Derived Artifact Stream API
        stream_res = client.get(f"/api/cases/{case_id}/derived-artifacts/{derived_id}/stream")
        assert stream_res.status_code == 200
        streamed_bytes = stream_res.content
        assert streamed_bytes == sqlite_plain
        print(f"  -> Stream API confirmed: byte-for-byte identical plaintext SQLite stream delivered")

        # 7. Check Operations Audit Log
        ops_res = client.get(f"/api/evidence/{evidence.id}/decryption/operations")
        assert ops_res.status_code == 200
        ops = ops_res.json()
        assert len(ops) >= 1
        assert ops[0]["status"] == "SUCCEEDED"
        print(f"  -> Decryption audit trail verified: operation #{ops[0]['operation_id']}")

        # 8. Assert ZERO local storage invariant
        post_uploads = list(uploads_dir.glob("*")) if uploads_dir.exists() else []
        post_reports = list(reports_dir.glob("*")) if reports_dir.exists() else []
        assert len(post_uploads) == 0, f"uploads/ leaked files: {post_uploads}"
        assert len(post_reports) == 0, f"reports/ leaked files: {post_reports}"
        print("  -> Zero-local-disk check passed: uploads/ and reports/ remain strictly empty!")

    finally:
        # Cleanup test case
        c = db.query(Case).filter(Case.id == case_id).first()
        if c:
            db.delete(c)
            db.commit()
        db.close()
        print(f"  -> Test case {case_id} cleaned up.")


if __name__ == "__main__":
    print("=" * 65)
    print("      ARTIFACTX PHASE E: R3 DECRYPTION VALIDATION SUITE        ")
    print("=" * 65)

    test_format_and_entropy_detector()
    test_whatsapp_key_parser_and_redaction()
    test_crypt12_decryption()
    test_crypt14_decryption()
    test_crypt15_decryption()
    test_whatsapp_media_hkdf_decryption()
    test_telegram_sqlcipher_decryption()
    test_telegram_mtproto_decryption()
    test_negative_security_and_authenticity()
    test_e2e_api_and_zero_disk_storage()

    print("\n" + "=" * 65)
    print("     ALL PHASE E R3 DECRYPTION TESTS PASSED! (10/10)           ")
    print("=" * 65)
