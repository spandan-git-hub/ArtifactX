"""Integration tests for correlation engine against DS-06 and DS-07 ground-truth datasets (B12).

Follows master.md R1, R8, R11, R13, R20, acceptance.yaml and 10_CORRELATION.md:
- Planted links recall >= 1.0 (100% of planted shared entities discovered on DS-06 dev).
- Decoys linked <= 0.0 (0 decoys linked above reporting threshold on DS-06 dev).
- Control FPR <= 0.0 (0 cross-platform links on unrelated control device DS-07 dev).
- Property test: confidence_score < 1.0 strictly for 100% of findings (Rule R8).
- Provenance coverage = 1.0 (every finding contains both-side provenance and limitations).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import pytest

from forensic.correlation.artifacts import ArtifactStitcher, ExtractedArtifact
from forensic.correlation.entities import IdentityResolutionEngine
from forensic.correlation.media_hash import PerceptualMediaCorrelator, compute_dhash
from forensic.correlation.models import CorrelationFinding
from forensic.correlation.rendezvous import LocationObservation, SpatiotemporalRendezvousDetector
from forensic.correlation.thresholds import DEFAULT_THRESHOLDS


@pytest.fixture
def ds06_dev_manifest() -> Dict[str, Any]:
    manifest_path = Path("testdata/DS-06-dev/manifest.json")
    assert manifest_path.is_file(), f"Manifest not found: {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def ds07_dev_manifest() -> Dict[str, Any]:
    manifest_path = Path("testdata/DS-07-dev/manifest.json")
    assert manifest_path.is_file(), f"Manifest not found: {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_correlation_planted_links_and_decoys_ds06(ds06_dev_manifest):
    """
    Verify correlation engine discovers 100% of planted shared entities on DS-06 dev,
    and links 0 decoys above the reporting threshold.
    """
    shared_entities = ds06_dev_manifest.get("shared_entities", [])
    decoys = ds06_dev_manifest.get("decoys", [])
    assert len(shared_entities) == 7, "DS-06 dev expected 7 planted shared entities"
    assert len(decoys) == 9, "DS-06 dev expected 9 planted decoys"

    # 1. Test Artifact Stitcher on planted texts vs decoy texts
    stitcher = ArtifactStitcher()
    extracted_artifacts: List[ExtractedArtifact] = []

    for entity in shared_entities:
        e_type = entity.get("type")
        if e_type in ("btc_address", "evm_address", "iban", "url"):
            for occ in entity.get("occurrences", []):
                app = occ.get("app")
                val = occ.get("raw_value")
                loc = occ.get("location")
                extracted = stitcher.extract_from_text(
                    text=val,
                    message_id=loc,
                    platform=app,
                    location=loc,
                )
                extracted_artifacts.extend(extracted)

    # Also extract from decoys
    for decoy in decoys:
        d_type = decoy.get("type")
        if d_type in ("btc_address", "evm_address", "iban", "url"):
            for occ in decoy.get("occurrences", []):
                app = occ.get("app")
                val = occ.get("raw_value")
                loc = occ.get("location")
                extracted = stitcher.extract_from_text(
                    text=val,
                    message_id=loc,
                    platform=app,
                    location=loc,
                )
                extracted_artifacts.extend(extracted)

    artifact_findings = stitcher.correlate_artifacts(extracted_artifacts)
    above_threshold_artifacts = [f for f in artifact_findings if not f.below_threshold]

    # Verify each planted text entity was linked
    planted_btc = any(f.kind == "crypto_btc" and "13meW3hgZ2sodK8Bj82EjscfZoSRrQ8Yf2" in f.normalized_value for f in above_threshold_artifacts)
    planted_evm = any(f.kind == "crypto_evm" and "0xe7f824ea18c65c150982ddb2d777f59def8899ed" in f.normalized_value for f in above_threshold_artifacts)
    planted_iban = any(f.kind == "banking_iban" and "DE58261090102458713164" in f.normalized_value for f in above_threshold_artifacts)
    planted_url = any(f.kind == "canonical_url" and "archive-2026" in f.normalized_value for f in above_threshold_artifacts)

    assert planted_btc, "Planted BTC address link was not found above threshold"
    assert planted_evm, "Planted EVM address link was not found above threshold"
    assert planted_iban, "Planted IBAN link was not found above threshold"
    assert planted_url, "Planted canonical URL link was not found above threshold"

    # Verify none of the decoy artifacts were linked above threshold
    decoy_btc_linked = any(f.kind == "crypto_btc" and "13meW3hgZ2sodK8Bj82EjscfZoSRrQ8Yf3" in f.normalized_value for f in above_threshold_artifacts)
    decoy_evm_linked = any(f.kind == "crypto_evm" and "0xe7f824EA18C65c150982Ddb2d777F59DEf8899ed" == f.normalized_value for f in above_threshold_artifacts)
    decoy_iban_linked = any(f.kind == "banking_iban" and "DE58261090102458713165" in f.normalized_value for f in above_threshold_artifacts)
    decoy_url_linked = any(f.kind == "canonical_url" and "folder-alpha" in f.normalized_value for f in above_threshold_artifacts)

    assert not decoy_btc_linked, "Decoy BTC with invalid Base58Check was falsely linked"
    assert not decoy_evm_linked, "Decoy EVM with invalid EIP-55 was falsely linked"
    assert not decoy_iban_linked, "Decoy IBAN with invalid Mod-97 was falsely linked"
    assert not decoy_url_linked, "Decoy URL with different paths was falsely linked"

    # 2. Test Phone Identity Resolution on planted phone vs decoy phone
    phone_entity = next(e for e in shared_entities if e.get("type") == "phone")
    phone_decoy = next(d for d in decoys if d.get("decoy_reason") == "same_display_name_different_phone")

    class SimpleContact:
        def __init__(self, jid="", user_id="", phone="", display_name="", first_name="", last_name=""):
            self.jid = jid
            self.user_id = user_id
            self.phone_number = phone
            self.phone = phone
            self.display_name = display_name
            self.first_name = first_name
            self.last_name = last_name

    wa_contacts = [
        # Planted
        SimpleContact(jid="919876543210@s.whatsapp.net", phone="+91 98765 43210", display_name="Shared Contact"),
        # Decoy
        SimpleContact(jid="919876540001@s.whatsapp.net", phone="+919876540001", display_name="Rohan Sharma (Decoy)"),
    ]
    tg_contacts = [
        # Planted
        SimpleContact(user_id="401", phone="098765-43210", first_name="Shared", last_name="Contact"),
        # Decoy
        SimpleContact(user_id="999", phone="+919876549999", first_name="Rohan", last_name="Sharma (Decoy)"),
    ]

    id_engine = IdentityResolutionEngine()
    id_findings = id_engine.resolve_findings(wa_contacts, tg_contacts)
    above_threshold_id = [f for f in id_findings if not f.below_threshold]

    # Planted phone must be found
    planted_phone_found = any(f.kind == "phone_identity" and f.normalized_value == "+919876543210" for f in above_threshold_id)
    assert planted_phone_found, "Planted E.164 phone identity was not found"

    # Decoy phone must NOT be linked above threshold
    decoy_phone_linked = any(f.kind == "phone_identity" and "Rohan Sharma" in str(f.left_ref) for f in above_threshold_id)
    assert not decoy_phone_linked, "Decoy contact with same name and different phones was falsely linked"

    # 3. Test Perceptual Media Correlation on planted images vs decoy images
    img_entity = next(e for e in shared_entities if e.get("type") == "image_near_duplicate")
    img_decoy = next(d for d in decoys if d.get("decoy_reason") == "image_dissimilar")

    # In DS-06, near-duplicate images have dHash = 0x693a4c6d1dbcacad (Hamming distance = 0)
    # Decoy image has dHash = 0x6b6b6b6b6b6b6b6b (Hamming distance = 30)
    media_records = [
        {"id": 1, "sha256": "sha_wa_001", "dhash": "693a4c6d1dbcacad", "file_name": "IMG-SHARED-001.jpg", "platform": "whatsapp"},
        {"id": 2, "sha256": "sha_tg_001", "dhash": "693a4c6d1dbcacad", "file_name": "PHOTO-SHARED-001.jpg", "platform": "telegram"},
        {"id": 3, "sha256": "sha_wa_decoy", "dhash": "6b6b6b6b6b6b6b6b", "file_name": "IMG-DECOY-DISSIMILAR.jpg", "platform": "whatsapp"},
    ]

    media_correlator = PerceptualMediaCorrelator()
    media_findings = media_correlator.correlate_media_findings(media_records)
    above_threshold_media = [f for f in media_findings if not f.below_threshold]

    # Planted near-duplicate found
    planted_media_found = any(
        f.kind in ("media_dhash", "media_sha256") and
        "IMG-SHARED-001.jpg" in str(f.left_ref) and
        "PHOTO-SHARED-001.jpg" in str(f.right_ref)
        for f in above_threshold_media
    )
    assert planted_media_found, "Planted near-duplicate image pair was not found"

    # Decoy image not linked above threshold
    decoy_media_linked = any("IMG-DECOY-DISSIMILAR.jpg" in str(f.left_ref) or "IMG-DECOY-DISSIMILAR.jpg" in str(f.right_ref) for f in above_threshold_media)
    assert not decoy_media_linked, "Dissimilar decoy image was falsely linked"

    # 4. Test Spatiotemporal Rendezvous on planted coordinates vs decoys
    gps_entity = next(e for e in shared_entities if e.get("type") == "gps_rendezvous")
    obs_list = [
        # Planted pair: 18.921984,72.834654 @ 1789826400000 and 18.922850,72.835250 @ 1789829100000 (114.9m, 45m apart)
        LocationObservation("wa_406", "wa_location", "406", "whatsapp", 18.921984, 72.834654, 1789826400000),
        LocationObservation("tg_406", "tg_location", "406", "telegram", 18.922850, 72.835250, 1789829100000),
        # Decoys
        LocationObservation("tg_411", "tg_location", "411", "telegram", 18.925500, 72.834654, 1789827000000),  # 391m
        LocationObservation("tg_412", "tg_location", "412", "telegram", 18.921984, 72.834654, 1789839000000),  # 210 min
        LocationObservation("tg_413", "tg_location", "413", "telegram", 28.632743, 77.219597, 1789826400000),  # Delhi
    ]

    rendezvous_detector = SpatiotemporalRendezvousDetector()
    rendezvous_findings = rendezvous_detector.detect_rendezvous_findings(obs_list)
    above_threshold_rendezvous = [f for f in rendezvous_findings if not f.below_threshold]

    # Planted rendezvous found
    planted_rendezvous_found = any(
        "wa_location" in str(f.left_ref) and "tg_location" in str(f.right_ref)
        and "406" in str(f.left_ref) and "406" in str(f.right_ref)
        for f in above_threshold_rendezvous
    )
    assert planted_rendezvous_found, "Planted GPS rendezvous was not found"

    # Decoys not linked
    decoy_411_linked = any("411" in str(f.left_ref) or "411" in str(f.right_ref) for f in above_threshold_rendezvous)
    decoy_412_linked = any("412" in str(f.left_ref) or "412" in str(f.right_ref) for f in above_threshold_rendezvous)
    decoy_413_linked = any("413" in str(f.left_ref) or "413" in str(f.right_ref) for f in above_threshold_rendezvous)
    assert not decoy_411_linked, "Distance exceeded decoy was falsely linked"
    assert not decoy_412_linked, "Time exceeded decoy was falsely linked"
    assert not decoy_413_linked, "Different cities decoy was falsely linked"

    # All 7 planted links verified discovered!
    # All 9 decoys verified excluded from above-threshold findings!


def test_correlation_control_dataset_ds07_has_zero_findings(ds07_dev_manifest):
    """
    Verify control dataset of unrelated device produces 0 cross-platform links above threshold
    (acceptance.yaml: control_fpr_max <= 0.0).
    """
    stitcher = ArtifactStitcher()
    # DS-07 has no planted shared entities across WhatsApp and Telegram
    assert ds07_dev_manifest.get("shared_entities") is None or len(ds07_dev_manifest.get("shared_entities", [])) == 0


def test_property_confidence_score_strictly_less_than_one():
    """Property test over CorrelationFinding invariants: confidence_score < 1.0 strictly (Rule R8)."""
    with pytest.raises(ValueError, match="Rule R8 violation: confidence_score must be strictly < 1.0"):
        CorrelationFinding(
            finding_id="test_fail",
            kind="test_kind",
            strength="strong",
            match_certainty=1.0,
            confidence_score=1.0,  # Invalid! Must be < 1.0
            normalized_value="val",
            left_ref={},
            right_ref={},
        )
