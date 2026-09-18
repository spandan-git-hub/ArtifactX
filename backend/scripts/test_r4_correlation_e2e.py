"""
ArtifactX Phase F: R4 Deep Cross-Platform Correlation Test Suite.
Validates all 17 requirements of Phase F:
1. Person Entity Model
2. Account / Entity Attribute Model
3. Identity Resolution Engine (Multi-Modal)
4. Evidence-Backed Edge Model
5. Platform Handover Detector
6. Configurable Handover Threshold
7. pHash Implementation (DCT-based)
8. dHash Implementation (Gradient-based)
9. Media Distance & Threshold Tests
10. Cryptocurrency Artifact Extraction & Checksums (BTC Base58Check, EVM, Tron, Monero)
11. Banking Artifact Extraction & Checksums (IBAN Mod-97, Credit Card Luhn, SWIFT, UPI)
12. Codeword & Logistical Extraction (Flight numbers, custom keywords)
13. GPS Spatiotemporal Rendezvous Detector (Haversine & delta-T)
14. Graph API & Stable JSON Graph Specification
15. Edge Drill-Down & Provenance Tracking
16. Ambiguous-Match Labeling & Judicial Disclaimers
17. Zero-Local-Disk Invariant
"""

import os
import sys
import io
import json
import time
import math
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal, Base, engine
from backend.models.models import Case, Evidence, WhatsAppMessage, WhatsAppContact, TelegramMessage, TelegramContact, MediaItem, PersonEntity, CorrelationFinding, CorrelationEdge

# Forensic module imports
from forensic.correlation.entities import (
    Person,
    EvidenceEdge,
    IdentityResolutionEngine,
    normalize_e164,
)
from forensic.correlation.handover import (
    PlatformHandoverDetector,
    PlatformHandoverCandidate,
)
from forensic.correlation.media_hash import (
    compute_dhash,
    compute_phash,
    hamming_distance,
    PerceptualMediaCorrelator,
)
from forensic.correlation.artifacts import (
    ArtifactStitcher,
    ExtractedArtifact,
    validate_btc_address,
    validate_evm_address,
    validate_tron_address,
    validate_monero_address,
    validate_iban,
    validate_luhn,
    validate_swift_bic,
    validate_upi_handle,
)
from forensic.correlation.rendezvous import (
    LocationObservation,
    RendezvousCandidate,
    SpatiotemporalRendezvousDetector,
    haversine_distance_meters,
)


def create_synthetic_image(color=(128, 128, 128), size=(100, 100), draw_shape=True) -> bytes:
    """Creates an in-memory PNG image."""
    img = Image.new("RGB", size, color)
    if draw_shape:
        # Draw a simple contrasting rectangle
        for x in range(20, 80):
            for y in range(20, 80):
                img.putpixel((x, y), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run_all_tests():
    print("=================================================================")
    print("    ARTIFACTX PHASE F: R4 DEEP CORRELATION VALIDATION SUITE      ")
    print("=================================================================\n")

    client = TestClient(app)
    db = SessionLocal()

    # Make sure all tables exist
    Base.metadata.create_all(bind=engine)

    # -------------------------------------------------------------
    # [Test 1] Person & Account Entity Model and Evidence Edge
    # -------------------------------------------------------------
    print("--- [Test 1] Person & Account Entity Models and Edge Structure ---")
    p = Person(
        person_id="person_test_001",
        label="John Doe",
        resolved_accounts=[
            {"platform": "whatsapp", "account_id": "1234567890@s.whatsapp.net"},
            {"platform": "telegram", "account_id": "99887766", "username": "johndoe"},
        ],
        phone_numbers=["+11234567890"],
        handles=["@johndoe"],
        aliases=["Johnny", "John D"],
        confidence_score=1.0,
        resolution_method="EXACT_E164_CORROBORATION",
        evidence_links=[{"platform": "whatsapp", "evidence_id": 1, "identifier": "1234567890@s.whatsapp.net"}],
        limitations=["Subject to carrier SIM reassignment."],
    )
    p_dict = p.to_dict()
    assert p_dict["person_id"] == "person_test_001"
    assert p_dict["confidence_score"] == 1.0
    assert len(p_dict["resolved_accounts"]) == 2
    assert p_dict["phone_numbers"] == ["+11234567890"]

    edge = EvidenceEdge(
        edge_id="edge_test_001",
        source_id="1234567890@s.whatsapp.net",
        source_type="whatsapp_jid",
        target_id="99887766",
        target_type="telegram_user",
        relation_type="SAME_ENTITY_CORROBORATED",
        strength_score=1.0,
        method="E164_PHONE_MATCH",
        source_observations=[{"evidence_id": 1, "phone": "+11234567890"}],
        limitations=["Carrier identity corroboration pending."],
    )
    edge_dict = edge.to_dict()
    assert edge_dict["strength_score"] == 1.0
    assert len(edge_dict["source_observations"]) == 1
    print("  -> Person entity model and evidence-backed edge verified.")

    # -------------------------------------------------------------
    # [Test 2] Identity Resolution Engine & Ambiguous Match Rule
    # -------------------------------------------------------------
    print("\n--- [Test 2] Identity Resolution Engine & Ambiguous Match Rule ---")
    engine_inst = IdentityResolutionEngine()

    class MockWAContact:
        def __init__(self, jid, name, phone, ev_id=1):
            self.jid = jid
            self.display_name = name
            self.phone_number = phone
            self.evidence_id = ev_id

    class MockTGContact:
        def __init__(self, uid, fn, ln, uname, phone, ev_id=2):
            self.user_id = uid
            self.first_name = fn
            self.last_name = ln
            self.username = uname
            self.phone = phone
            self.evidence_id = ev_id

    # 1. Exact phone match -> should create Person cluster
    wa_contacts = [
        MockWAContact("15551234567@s.whatsapp.net", "Alice Smith", "+15551234567"),
        # 2. Similar name BUT DIFFERENT/NO PHONE -> must NOT merge into Person!
        MockWAContact("18889990000@s.whatsapp.net", "Robert Brown", "+18889990000"),
    ]
    tg_contacts = [
        MockTGContact(77001, "Alice", "Smith", "alice_s", "+15551234567"),
        MockTGContact(77002, "Robert", "Brown", "robbie_b", "+17770001111"),
    ]

    res = engine_inst.resolve(wa_contacts, tg_contacts)
    persons_out = res["persons"]
    edges_out = res["edges"]
    ambig_out = res["ambiguous_candidates"]

    assert len(persons_out) == 1, f"Expected exactly 1 resolved Person, got {len(persons_out)}"
    assert persons_out[0]["phone_numbers"] == ["+15551234567"]
    assert persons_out[0]["confidence_score"] == 1.0

    # Robert Brown must be marked as ambiguous candidate, NOT merged into Person
    assert len(ambig_out) == 1, f"Expected 1 ambiguous candidate, got {len(ambig_out)}"
    assert ambig_out[0]["wa_name"].lower() == "robert brown"
    assert ambig_out[0]["tg_name"].lower() == "robert brown"

    # Verify edge has is_ambiguous = True
    ambig_edge = next((e for e in edges_out if e.get("is_ambiguous")), None)
    assert ambig_edge is not None
    assert "JUDICIAL INVARIANT" in ambig_edge["limitations"][0]
    print("  -> Exact E.164 corroboration resolved accurately.")
    print("  -> Judicial rule enforced: Name similarity alone flagged as ambiguous, not merged into Person.")

    # -------------------------------------------------------------
    # [Test 3] Platform Handover Detector & Configurable Threshold
    # -------------------------------------------------------------
    print("\n--- [Test 3] Platform Handover Detector & Configurable Threshold ---")
    detector = PlatformHandoverDetector(default_threshold_seconds=180)

    class MockMsg:
        def __init__(self, mid, body, ts, sender):
            self.message_id = mid
            self.body = body
            self.timestamp = ts
            self.sender_jid = sender
            self.sender_id = sender

    base_time = 1700000000
    # WhatsApp message saying 'switch to telegram' at T=0
    wa_msg = MockMsg("wa_m1", "Hey let's switch to telegram now", base_time, "alice@s.whatsapp.net")
    # Telegram message at T=45s
    tg_msg1 = MockMsg(5001, "Hey I'm on tg now", base_time + 45, 77001)
    # Telegram message at T=250s (outside default 180s threshold)
    tg_msg2 = MockMsg(5002, "Are you there?", base_time + 250, 77001)

    handovers_180 = detector.detect_handovers([wa_msg], [tg_msg1, tg_msg2], threshold_seconds=180)
    assert len(handovers_180) == 1
    assert handovers_180[0].time_delta_seconds == 45
    assert handovers_180[0].classification == "PLATFORM_HANDOVER_CANDIDATE"
    assert "switch to telegram" in handovers_180[0].transition_keywords[0].lower()

    # Now test configurable threshold widened to 300s -> should catch both
    handovers_300 = detector.detect_handovers([wa_msg], [tg_msg1, tg_msg2], threshold_seconds=300)
    assert len(handovers_300) == 2
    assert handovers_300[1].time_delta_seconds == 250
    print("  -> Platform handover candidates detected within 45s proximity.")
    print("  -> Configurable threshold (180s vs 300s) successfully adjusted detection window.")
    print("  -> Neutral classification 'PLATFORM_HANDOVER_CANDIDATE' confirmed.")

    # -------------------------------------------------------------
    # [Test 4] Perceptual Media Hashing (dHash & pHash)
    # -------------------------------------------------------------
    print("\n--- [Test 4] Perceptual Media Hashing (dHash & pHash) ---")
    img_bytes1 = create_synthetic_image((100, 100, 100), (120, 120))
    # Resized copy of the same image (simulating mobile preview / thumbnail)
    with Image.open(io.BytesIO(img_bytes1)) as im1:
        buf2 = io.BytesIO()
        im1.resize((90, 90)).save(buf2, format="PNG")
        img_bytes2 = buf2.getvalue()
    # Completely different image (solid white, no shape)
    img_bytes3 = create_synthetic_image((255, 255, 255), (120, 120), draw_shape=False)

    dhash1 = compute_dhash(img_bytes1)
    dhash2 = compute_dhash(img_bytes2)
    dhash3 = compute_dhash(img_bytes3)

    phash1 = compute_phash(img_bytes1)
    phash2 = compute_phash(img_bytes2)
    phash3 = compute_phash(img_bytes3)

    assert len(dhash1) == 16, f"Expected 16 hex chars for dHash, got {len(dhash1)}"
    assert len(phash1) == 16, f"Expected 16 hex chars for pHash, got {len(phash1)}"

    # Identical visual content with different dimensions should have 0 or very low Hamming distance
    dist_same_d = hamming_distance(dhash1, dhash2)
    dist_same_p = hamming_distance(phash1, phash2)
    assert dist_same_d <= 4, f"dHash distance between resized images too high: {dist_same_d}"
    assert dist_same_p <= 4, f"pHash distance between resized images too high: {dist_same_p}"

    # Different images should have significant distance
    dist_diff = hamming_distance(phash1, phash3)
    assert dist_diff > 10, f"Distance between different images should be >10, got {dist_diff}"

    # Test Correlator
    media_correlator = PerceptualMediaCorrelator(default_threshold=4)
    media_records = [
        {"id": 101, "file_name": "photo_120.png", "sha256": "hashA", "dhash": dhash1, "phash": phash1},
        {"id": 102, "file_name": "photo_90.png", "sha256": "hashB", "dhash": dhash2, "phash": phash2},
        {"id": 103, "file_name": "blank.png", "sha256": "hashC", "dhash": dhash3, "phash": phash3},
    ]
    matches = media_correlator.correlate_items(media_records, threshold=4)
    assert len(matches) == 1
    assert matches[0]["source_media_id"] == 101 and matches[0]["target_media_id"] == 102
    assert matches[0]["classification"] == "PERCEPTUAL_MEDIA_MATCH"
    print("  -> dHash (gradient) and pHash (2D-DCT) computed successfully.")
    print("  -> Resized image pair linked with Hamming distance <= 4.")
    print("  -> Dissimilar image rejected.")

    # -------------------------------------------------------------
    # [Test 5] Deterministic Artifact Extractors & Checksum Validators
    # -------------------------------------------------------------
    print("\n--- [Test 5] Deterministic Artifact Extractors & Checksum Validators ---")

    # Bitcoin: valid legacy P2PKH (with Base58Check) and valid Bech32
    btc_valid_legacy = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis address
    btc_valid_bech32 = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
    btc_invalid = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfXX"  # Corrupted checksum

    assert validate_btc_address(btc_valid_legacy) is True
    assert validate_btc_address(btc_valid_bech32) is True
    assert validate_btc_address(btc_invalid) is False

    # EVM address
    evm_valid = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
    evm_invalid = "0x71C7656EC7ab88b098defB751B7401B5f6d897"  # too short
    assert validate_evm_address(evm_valid) is True
    assert validate_evm_address(evm_invalid) is False

    # Tron & Monero
    tron_valid = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
    monero_valid = "44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXft3XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A"
    assert validate_tron_address(tron_valid) is True
    assert validate_monero_address(monero_valid) is True

    # IBAN Mod-97 checksum
    # Valid German test IBAN: DE89 3704 0044 0532 0130 00
    iban_valid = "DE89370400440532013000"
    iban_invalid = "DE89370400440532013001"  # bad check digits
    assert validate_iban(iban_valid) is True
    assert validate_iban(iban_invalid) is False

    # Credit Card Luhn check
    cc_valid = "4532715012345676"  # Valid Visa Luhn
    cc_invalid = "4532715012345678"  # Invalid Luhn
    assert validate_luhn(cc_valid) is True
    assert validate_luhn(cc_invalid) is False

    # SWIFT and UPI
    assert validate_swift_bic("DEUTDEDD") is True
    assert validate_swift_bic("INVALIDTOOLONG123") is False
    assert validate_upi_handle("examiner@okhdfcbank") is True
    assert validate_upi_handle("john.doe@gmail.com") is False  # Email filtered out

    # Test full ArtifactStitcher in text
    stitcher = ArtifactStitcher(custom_keywords=["dead drop", "munitions"])
    sample_text = (
        f"Send the payment to BTC {btc_valid_legacy} or ETH {evm_valid}. "
        f"Wire remaining funds to IBAN {iban_valid}. "
        f"Meet at the dead drop near the terminal for flight AA123."
    )
    extracted = stitcher.extract_from_text(sample_text, message_id="m99", platform="telegram")

    extracted_types = {e.artifact_type for e in extracted}
    assert "BITCOIN" in extracted_types
    assert "EVM" in extracted_types
    assert "IBAN" in extracted_types
    assert "FLIGHT_NUMBER" in extracted_types
    assert "CUSTOM_KEYWORD" in extracted_types

    # Verify checksum statuses
    btc_art = next(e for e in extracted if e.artifact_type == "BITCOIN")
    assert btc_art.validation_status == "VALIDATED_CHECKSUM_OK"
    iban_art = next(e for e in extracted if e.artifact_type == "IBAN")
    assert iban_art.validation_status == "VALIDATED_CHECKSUM_OK"

    print("  -> Bitcoin Base58Check and Bech32 validation verified.")
    print("  -> EVM, Tron, and Monero syntax verification passed.")
    print("  -> ISO 7064 Mod-97 IBAN checksum validator verified.")
    print("  -> Luhn mod-10 card validator passed (invalid card rejected).")
    print("  -> Custom codewords ('dead drop') and flight numbers extracted.")

    # -------------------------------------------------------------
    # [Test 6] Spatiotemporal Rendezvous Detector (Haversine & Time)
    # -------------------------------------------------------------
    print("\n--- [Test 6] Spatiotemporal Rendezvous Detector ---")
    # Coordinates in Central Park NYC:
    # Point 1: 40.785091, -73.968285
    # Point 2: 40.785300, -73.968100 (~28 meters away)
    # Point 3: 40.800000, -73.960000 (~1.7 km away)
    lat1, lon1 = 40.785091, -73.968285
    lat2, lon2 = 40.785300, -73.968100
    lat3, lon3 = 40.800000, -73.960000

    dist_near = haversine_distance_meters(lat1, lon1, lat2, lon2)
    dist_far = haversine_distance_meters(lat1, lon1, lat3, lon3)
    assert 20.0 < dist_near < 35.0, f"Unexpected near distance: {dist_near}"
    assert dist_far > 1500.0, f"Unexpected far distance: {dist_far}"

    obs1 = LocationObservation("loc1", "media_exif", "med1", "media", lat1, lon1, timestamp=1700000000)
    obs2 = LocationObservation("loc2", "wa_location", "wa1", "whatsapp", lat2, lon2, timestamp=1700000300)  # +5 min, 28m away
    obs3 = LocationObservation("loc3", "tg_location", "tg1", "telegram", lat3, lon3, timestamp=1700000400)  # far away

    rendezvous_detector = SpatiotemporalRendezvousDetector(
        default_distance_threshold_meters=50.0,
        default_time_threshold_seconds=1800,
    )
    rc_list = rendezvous_detector.detect_rendezvous([obs1, obs2, obs3])
    assert len(rc_list) == 1
    assert rc_list[0].distance_meters < 35.0
    assert rc_list[0].time_delta_seconds == 300
    assert rc_list[0].classification == "SPATIOTEMPORAL_RENDEZVOUS_CANDIDATE"
    assert "GPS accuracy" in rc_list[0].limitations[1]
    print("  -> Haversine great-circle calculation confirmed (~28m accurate).")
    print("  -> Rendezvous event detected under 50m and 1800s thresholds.")
    print("  -> Far co-occurrence (>1.5km) filtered out.")

    # -------------------------------------------------------------
    # [Test 7] End-to-End Deep Correlation API & Database Verification
    # -------------------------------------------------------------
    print("\n--- [Test 7] End-to-End Deep Correlation API & Database Verification ---")
    test_case = Case(
        name="R4 Deep Correlation Test Case",
        description="Automated forensic test case for R4",
        investigator="Det. Agent",
        status="active",
    )
    db.add(test_case)
    db.commit()
    case_id = test_case.id

    # Add evidence records
    ev_wa = Evidence(
        case_id=case_id,
        original_filename="whatsapp_exhibit.zip",
        storage_path="pg://evidence/wa",
        sha256="a" * 64,
        evidence_type="whatsapp",
    )
    ev_tg = Evidence(
        case_id=case_id,
        original_filename="telegram_exhibit.zip",
        storage_path="pg://evidence/tg",
        sha256="b" * 64,
        evidence_type="telegram",
    )
    db.add_all([ev_wa, ev_tg])
    db.commit()

    # Add WhatsApp Contact & Message with BTC and Handover phrase
    wa_c = WhatsAppContact(
        evidence_id=ev_wa.id,
        jid="19998887777@s.whatsapp.net",
        display_name="Charlie Delta",
        phone_number="+19998887777",
        status="active",
    )
    wa_m = WhatsAppMessage(
        evidence_id=ev_wa.id,
        message_id="wa_msg_101",
        key_remote_jid="19998887777@s.whatsapp.net",
        sender_jid="19998887777@s.whatsapp.net",
        participant_jid="",
        body=f"Switch to telegram immediately. Transfer to BTC {btc_valid_legacy}",
        timestamp=1700000000,
        status="received",
    )

    # Add Telegram Contact & Message with same phone and response at +30s
    tg_c = TelegramContact(
        evidence_id=ev_tg.id,
        user_id=889900,
        first_name="Charlie",
        last_name="Delta",
        username="charliedelta",
        phone="+19998887777",
    )
    tg_m = TelegramMessage(
        evidence_id=ev_tg.id,
        message_id=202,
        dialog_id="889900",
        sender_id=889900,
        body=f"Connected on telegram. IBAN is {iban_valid}",
        timestamp=1700000030,
    )

    # Add Media item with GPS EXIF
    media1 = MediaItem(
        case_id=case_id,
        evidence_id=ev_wa.id,
        file_path="IMG_001.jpg",
        sha256="c" * 64,
        mime_type="image/jpeg",
        media_type="image",
        file_size=12000,
        exif_data={
            "GPSLatitude": lat1,
            "GPSLongitude": lon1,
            "timestamp": 1700000000,
            "dhash": dhash1,
            "phash": phash1,
        }
    )
    media2 = MediaItem(
        case_id=case_id,
        evidence_id=ev_tg.id,
        file_path="PHOTO_002.jpg",
        sha256="d" * 64,
        mime_type="image/jpeg",
        media_type="image",
        file_size=12000,
        exif_data={
            "GPSLatitude": lat2,
            "GPSLongitude": lon2,
            "timestamp": 1700000060,
            "dhash": dhash2,
            "phash": phash2,
        }
    )

    db.add_all([wa_c, wa_m, tg_c, tg_m, media1, media2])
    db.commit()
    db.close()

    # Trigger Deep Correlation API
    resp = client.post(
        f"/api/cases/{case_id}/correlation/deep/run",
        json={
            "handover_threshold_seconds": 180,
            "media_hamming_distance": 4,
            "rendezvous_distance_meters": 50.0,
            "rendezvous_time_seconds": 1800,
            "custom_keywords": ["transfer", "immediately"],
        }
    )
    assert resp.status_code == 200, f"Deep correlation API failed: {resp.text}"
    deep_res = resp.json()
    db = SessionLocal()
    assert deep_res["status"] == "SUCCEEDED"
    assert deep_res["persons_count"] >= 1
    assert deep_res["handovers_count"] >= 1
    assert deep_res["media_matches_count"] >= 1
    assert deep_res["artifacts_count"] >= 2
    assert deep_res["rendezvous_count"] >= 1

    # Verify Database Tables
    person_records = db.query(PersonEntity).filter(PersonEntity.case_id == case_id).all()
    assert len(person_records) >= 1
    assert person_records[0].confidence_score == 1.0
    assert "+19998887777" in person_records[0].attributes["phone_numbers"]

    finding_records = db.query(CorrelationFinding).filter(CorrelationFinding.case_id == case_id).all()
    finding_types = {f.finding_type for f in finding_records}
    assert "handover" in finding_types
    assert "media_match" in finding_types
    assert "shared_artifact" in finding_types
    assert "rendezvous" in finding_types

    # Verify Graph Endpoint
    graph_resp = client.get(f"/api/cases/{case_id}/correlation/graph")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert "nodes" in graph_data and len(graph_data["nodes"]) > 0
    assert "edges" in graph_data and len(graph_data["edges"]) > 0
    assert "metadata" in graph_data
    assert graph_data["metadata"]["algorithm_version"] == "1.0.0"

    # Verify Handovers Endpoint
    ho_resp = client.get(f"/api/cases/{case_id}/correlation/handover")
    assert ho_resp.status_code == 200
    assert len(ho_resp.json()) >= 1

    # Verify Media Endpoint
    med_resp = client.get(f"/api/cases/{case_id}/correlation/media")
    assert med_resp.status_code == 200
    assert len(med_resp.json()) >= 1

    # Verify Artifacts Endpoint
    art_resp = client.get(f"/api/cases/{case_id}/correlation/artifacts")
    assert art_resp.status_code == 200
    assert len(art_resp.json()) >= 2

    # Verify Rendezvous Endpoint
    rdv_resp = client.get(f"/api/cases/{case_id}/correlation/rendezvous")
    assert rdv_resp.status_code == 200
    assert len(rdv_resp.json()) >= 1

    # Verify Persons Endpoint
    prs_resp = client.get(f"/api/cases/{case_id}/correlation/persons")
    assert prs_resp.status_code == 200
    assert len(prs_resp.json()) >= 1

    print("  -> Deep correlation REST API executed cleanly.")
    print("  -> PostgreSQL persistence of PersonEntity and CorrelationFinding confirmed.")
    print("  -> Stable JSON graph structure verified (nodes, edges, metadata).")
    print("  -> Specialized R4 query endpoints validated.")

    # -------------------------------------------------------------
    # [Test 8] Edge Drill-Down & Provenance Tracking
    # -------------------------------------------------------------
    print("\n--- [Test 8] Edge Drill-Down & Provenance Tracking ---")
    for edge in graph_data["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "relation_type" in edge
        assert "strength_score" in edge
        assert "method" in edge
        assert "source_observations" in edge
        assert "limitations" in edge
    print("  -> Every edge exposes underlying source observations and method provenance.")

    # -------------------------------------------------------------
    # [Test 9] Zero-Local-Disk Invariant & Database Cleanup
    # -------------------------------------------------------------
    print("\n--- [Test 9] Zero-Local-Disk Invariant & Case Cleanup ---")
    # Clean up test case and associated exhibits
    ev_ids_to_delete = [e.id for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()]
    db.query(CorrelationFinding).filter(CorrelationFinding.case_id == case_id).delete()
    db.query(PersonEntity).filter(PersonEntity.case_id == case_id).delete()
    db.query(CorrelationEdge).filter(CorrelationEdge.case_id == case_id).delete()
    db.query(MediaItem).filter(MediaItem.case_id == case_id).delete()
    if ev_ids_to_delete:
        db.query(WhatsAppMessage).filter(WhatsAppMessage.evidence_id.in_(ev_ids_to_delete)).delete()
        db.query(WhatsAppContact).filter(WhatsAppContact.evidence_id.in_(ev_ids_to_delete)).delete()
        db.query(TelegramMessage).filter(TelegramMessage.evidence_id.in_(ev_ids_to_delete)).delete()
        db.query(TelegramContact).filter(TelegramContact.evidence_id.in_(ev_ids_to_delete)).delete()
    db.query(Evidence).filter(Evidence.case_id == case_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.commit()

    uploads_dir = PROJECT_ROOT / "uploads"
    reports_dir = PROJECT_ROOT / "reports"
    uploads_files = [f for f in uploads_dir.iterdir() if f.is_file()] if uploads_dir.exists() else []
    reports_files = [f for f in reports_dir.iterdir() if f.is_file()] if reports_dir.exists() else []

    assert len(uploads_files) == 0, f"uploads/ not empty: {uploads_files}"
    assert len(reports_files) == 0, f"reports/ not empty: {reports_files}"
    print("  -> Zero-local-disk target satisfied: uploads/ and reports/ remain strictly empty.")
    print(f"  -> Test case {case_id} cleaned up successfully.")

    db.close()
    print("\n=================================================================")
    print("     ALL PHASE F R4 CORRELATION TESTS PASSED! (9/9)             ")
    print("=================================================================")


if __name__ == "__main__":
    run_all_tests()
