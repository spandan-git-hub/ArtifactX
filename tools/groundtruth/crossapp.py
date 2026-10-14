"""Cross-app (DS-06), Control (DS-07), and Tamper (DS-08) dataset generators.

Follows master.md R1, R6, R11, R14, R20 and 02_GROUND_TRUTH_DATASETS.md §5:
- Planted shared entities across WhatsApp and Telegram (phone, BTC, EVM, IBAN, URL, near-duplicate image, GPS rendezvous).
- Decoys across WhatsApp and Telegram that must NOT link (invalid checksums, different paths, display-name only, dissimilar image, rendezvous time/distance exceeded).
- Control dataset (DS-07) from an unrelated device with 0 shared entities.
- Tamper dataset (DS-08) with single-byte flips at recorded offsets.
- Purely deterministic; derived strictly from DeterministicRNG(seed).
"""

from __future__ import annotations

import hashlib
import io
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from PIL import Image

# UTF-8 stdout encoding safeguard on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tools.groundtruth.crypto.bitcoin_address import (
    base58check_validate,
    generate_btc_decoy_address,
    generate_deterministic_btc_address,
)
from tools.groundtruth.crypto.evm_address import (
    generate_deterministic_evm_address,
    generate_evm_decoy_address,
    validate_evm_address,
)
from tools.groundtruth.crypto.iban import (
    generate_deterministic_iban,
    generate_iban_decoy,
    validate_iban,
)
from tools.groundtruth.manifest import DatasetFileInfo, DatasetManifest
from tools.groundtruth.rng import DeterministicRNG
from tools.groundtruth.tg.generator import generate_telegram_dataset
from tools.groundtruth.wa.generator import generate_whatsapp_plain_dataset


# =============================================================================
# Helper Utilities (Pure, Deterministic)
# =============================================================================

def normalize_url(raw_url: str) -> str:
    """Normalize a URL per B12.3 specification."""
    parsed = urlparse(raw_url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = parsed.path
    if path == "/":
        path = ""

    tracking_prefixes = ("utm_", "fbclid", "gclid", "ref", "campaign")
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {
        k: v for k, v in query_params.items()
        if not any(k.lower().startswith(p) for p in tracking_prefixes)
    }
    filtered_query = urlencode(filtered_params, doseq=True)
    return urlunparse((scheme, netloc, path, "", filtered_query, ""))


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute Haversine distance in meters between two WGS84 coordinates."""
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def compute_image_dhash(img_bytes: bytes) -> int:
    """Compute 64-bit difference hash (dHash) from image bytes."""
    with Image.open(io.BytesIO(img_bytes)) as img:
        gray = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = [gray.getpixel((col, row)) for row in range(8) for col in range(9)]

    diff = []
    for row in range(8):
        for col in range(8):
            diff.append(pixels[row * 9 + col] > pixels[row * 9 + col + 1])

    h = 0
    for bit in diff:
        h = (h << 1) | int(bit)
    return h


def dhash_hamming_distance(h1: int, h2: int) -> int:
    """Compute Hamming distance between two 64-bit integer hashes."""
    return (h1 ^ h2).bit_count()


def _compute_sha256(path: Path) -> Tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


# =============================================================================
# B4.1 / DS-06: Cross-App Dataset Generator
# =============================================================================

def generate_crossapp_dataset(
    output_dir: Path,
    dataset_id: str = "DS-06",
    variant: str = "dev",
    seed: Optional[int] = None,
) -> DatasetManifest:
    """Generate the cross-app ground-truth dataset (DS-06)."""
    if seed is None:
        seed = 20261016 if variant == "dev" else 6102602

    rng = DeterministicRNG(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Prepare Media Directory & Generate Shared Images
    wa_img_dir = output_dir / "Media" / "WhatsApp Images"
    wa_img_dir.mkdir(parents=True, exist_ok=True)
    tg_img_dir = output_dir / "Media" / "Telegram"
    tg_img_dir.mkdir(parents=True, exist_ok=True)

    # Base image for near-duplicate pair
    base_img = Image.new("RGB", (128, 128), color=(240, 240, 245))
    for y in range(0, 128, 16):
        for x in range(0, 128, 16):
            c_val = (rng.randint(30, 220), rng.randint(40, 210), rng.randint(50, 230))
            for py in range(y, min(y + 16, 128)):
                for px in range(x, min(x + 16, 128)):
                    base_img.putpixel((px, py), c_val)

    wa_img_path = wa_img_dir / "IMG-SHARED-001.jpg"
    base_img.save(wa_img_path, format="JPEG", quality=90)
    wa_dhash = compute_image_dhash(wa_img_path.read_bytes())

    near_dup = base_img.resize((120, 120), Image.Resampling.LANCZOS)
    tg_img_path = tg_img_dir / "PHOTO-SHARED-001.jpg"
    near_dup.save(tg_img_path, format="JPEG", quality=85)
    tg_dhash = compute_image_dhash(tg_img_path.read_bytes())

    dist_near_dup = dhash_hamming_distance(wa_dhash, tg_dhash)
    assert dist_near_dup <= 4, f"Near-duplicate dHash distance too high: {dist_near_dup}"

    # Dissimilar image for decoy
    decoy_base = Image.new("RGB", (128, 128), color=(20, 20, 30))
    for x in range(0, 128, 8):
        c_val = (rng.randint(150, 255), rng.randint(20, 80), rng.randint(20, 80))
        for py in range(128):
            for px in range(x, min(x + 8, 128)):
                decoy_base.putpixel((px, py), c_val)

    wa_decoy_img_path = wa_img_dir / "IMG-DECOY-DISSIMILAR.jpg"
    decoy_base.save(wa_decoy_img_path, format="JPEG", quality=90)
    decoy_dhash = compute_image_dhash(wa_decoy_img_path.read_bytes())
    dist_decoy = dhash_hamming_distance(wa_dhash, decoy_dhash)
    assert dist_decoy >= 10, f"Decoy image distance too low: {dist_decoy}"

    # 2. Shared Entities Setup
    phone_digits_suffix = "43210" if variant == "dev" else "48811"
    wa_phone_raw = f"+91 98765 {phone_digits_suffix}"
    tg_phone_raw = f"098765-{phone_digits_suffix}"
    norm_phone = f"+9198765{phone_digits_suffix}"

    btc_valid = generate_deterministic_btc_address(rng)
    btc_decoy = generate_btc_decoy_address(btc_valid)

    evm_valid = generate_deterministic_evm_address(rng)
    evm_decoy = generate_evm_decoy_address(evm_valid)

    iban_valid = generate_deterministic_iban(rng, country_code="DE")
    iban_spaced = f"{iban_valid[:4]} {iban_valid[4:8]} {iban_valid[8:12]} {iban_valid[12:16]} {iban_valid[16:20]} {iban_valid[20:]}".strip()
    iban_decoy = generate_iban_decoy(iban_valid)

    base_url = "https://example.test/case-files/archive-2026"
    wa_url_raw = "https://www.example.test/case-files/archive-2026?utm_source=whatsapp&utm_medium=chat"
    tg_url_raw = "https://example.test/case-files/archive-2026?utm_source=telegram&utm_campaign=audit"

    rendezvous_ts_wa = 1789826400000
    rendezvous_ts_tg = rendezvous_ts_wa + 45 * 60 * 1000
    r_dist = haversine_distance_m(18.921984, 72.834654, 18.922850, 72.835250)

    # 3. Build WhatsApp Extra Messages
    wa_extra_messages = [
        {"row_id": 401, "key_id": "SHARED_PLANT_WA_PHONE", "ts": 1726050010000, "text": f"Please contact investigator on {wa_phone_raw} for briefing.", "type_code": 0},
        {"row_id": 402, "key_id": "SHARED_PLANT_WA_BTC", "ts": 1726050020000, "text": f"Settlement ledger BTC address confirmed: {btc_valid}", "type_code": 0},
        {"row_id": 403, "key_id": "SHARED_PLANT_WA_EVM", "ts": 1726050030000, "text": f"Smart contract depository EVM address: {evm_valid}", "type_code": 0},
        {"row_id": 404, "key_id": "SHARED_PLANT_WA_IBAN", "ts": 1726050040000, "text": f"Wire instructions: send to IBAN {iban_spaced}", "type_code": 0},
        {"row_id": 405, "key_id": "SHARED_PLANT_WA_URL", "ts": 1726050050000, "text": f"Review dossier: {wa_url_raw}", "type_code": 0},
        {"row_id": 406, "key_id": "SHARED_PLANT_WA_GPS", "ts": rendezvous_ts_wa, "text": "Rendezvous point coordinate pin", "type_code": 5, "latitude": 18.921984, "longitude": 72.834654},
        {"row_id": 407, "key_id": "DECOY_PLANT_WA_BTC", "ts": 1726050060000, "text": f"Candidate address invalid: {btc_decoy}", "type_code": 0},
        {"row_id": 408, "key_id": "DECOY_PLANT_WA_EVM", "ts": 1726050070000, "text": f"Unverified address rejected: {evm_decoy}", "type_code": 0},
        {"row_id": 409, "key_id": "DECOY_PLANT_WA_IBAN", "ts": 1726050080000, "text": f"Wire failed for IBAN: {iban_decoy}", "type_code": 0},
        {"row_id": 410, "key_id": "DECOY_PLANT_WA_URL", "ts": 1726050090000, "text": "Review alpha: https://example.test/case-files/folder-alpha", "type_code": 0},
        {"row_id": 411, "key_id": "DECOY_PLANT_WA_GPS_DIST", "ts": rendezvous_ts_wa, "text": "Location pin test", "type_code": 5, "latitude": 18.921984, "longitude": 72.834654},
        {"row_id": 412, "key_id": "DECOY_PLANT_WA_GPS_TIME", "ts": rendezvous_ts_wa, "text": "Location pin test time decoy", "type_code": 5, "latitude": 18.921984, "longitude": 72.834654},
        {"row_id": 413, "key_id": "DECOY_PLANT_WA_GPS_PLACE", "ts": rendezvous_ts_wa, "text": "Location pin test place decoy", "type_code": 5, "latitude": 18.921984, "longitude": 72.834654},
    ]

    # 4. Build Telegram Extra Messages
    tg_extra_messages = [
        {"mid": 401, "uid": 1001, "date": 1726050010, "text": f"Contact details received: call {tg_phone_raw} regarding the handover.", "type_code": 0},
        {"mid": 402, "uid": 1001, "date": 1726050020, "text": f"Sending tranche to BTC: {btc_valid}", "type_code": 0},
        {"mid": 403, "uid": 1001, "date": 1726050030, "text": f"Verified audit target EVM: {evm_valid}", "type_code": 0},
        {"mid": 404, "uid": 1001, "date": 1726050040, "text": f"Confirmed receiving account IBAN: {iban_valid}", "type_code": 0},
        {"mid": 405, "uid": 1001, "date": 1726050050, "text": f"Dossier reference: {tg_url_raw}", "type_code": 0},
        {"mid": 406, "uid": 1001, "date": int(rendezvous_ts_tg / 1000), "text": "Rendezvous location arrival (photo attached)", "type_code": 5, "latitude": 18.922850, "longitude": 72.835250},
        {"mid": 407, "uid": 1001, "date": 1726050060, "text": f"Do not use this address: {btc_decoy}", "type_code": 0},
        {"mid": 408, "uid": 1001, "date": 1726050070, "text": f"Checksum mismatch warning for {evm_decoy}", "type_code": 0},
        {"mid": 409, "uid": 1001, "date": 1726050080, "text": f"Bank error code 97 on account: {iban_decoy}", "type_code": 0},
        {"mid": 410, "uid": 1001, "date": 1726050090, "text": "Review beta: https://example.test/case-files/folder-beta", "type_code": 0},
        {"mid": 411, "uid": 1001, "date": int((rendezvous_ts_wa + 600000) / 1000), "text": "Distance decoy location pin", "type_code": 5, "latitude": 18.925500, "longitude": 72.834654},
        {"mid": 412, "uid": 1001, "date": int((rendezvous_ts_wa + 210 * 60 * 1000) / 1000), "text": "Time decoy location pin", "type_code": 5, "latitude": 18.921984, "longitude": 72.834654},
        {"mid": 413, "uid": 1001, "date": int(rendezvous_ts_wa / 1000), "text": "Delhi place decoy location pin", "type_code": 5, "latitude": 28.632743, "longitude": 77.219597},
    ]

    # 5. Generate databases with extra messages integrated during creation
    wa_manifest = generate_whatsapp_plain_dataset(
        output_dir=output_dir,
        dataset_id=dataset_id,
        variant=variant,
        seed=seed + 100,
        extra_messages=wa_extra_messages,
    )

    tg_manifest = generate_telegram_dataset(
        output_dir=output_dir,
        dataset_id=dataset_id,
        variant=variant,
        seed=seed + 200,
        extra_messages=tg_extra_messages,
    )

    # 6. Shared Entities Manifest Entries
    shared_entities = [
        {
            "type": "phone",
            "value_norm": norm_phone,
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_401", "raw_value": wa_phone_raw},
                {"app": "telegram", "location": "messages_v2_mid_401", "raw_value": tg_phone_raw},
            ],
            "expected_link": True,
            "notes": "Same E.164 phone number with differing national and international formatting",
        },
        {
            "type": "btc_address",
            "value_norm": btc_valid,
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_402", "raw_value": btc_valid},
                {"app": "telegram", "location": "messages_v2_mid_402", "raw_value": btc_valid},
            ],
            "expected_link": True,
            "notes": "Valid Bitcoin Base58Check address shared across both platforms",
        },
        {
            "type": "evm_address",
            "value_norm": evm_valid.lower(),
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_403", "raw_value": evm_valid},
                {"app": "telegram", "location": "messages_v2_mid_403", "raw_value": evm_valid},
            ],
            "expected_link": True,
            "notes": "Valid Ethereum EIP-55 mixed-case checksummed address",
        },
        {
            "type": "iban",
            "value_norm": iban_valid,
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_404", "raw_value": iban_spaced},
                {"app": "telegram", "location": "messages_v2_mid_404", "raw_value": iban_valid},
            ],
            "expected_link": True,
            "notes": "Valid ISO 7064 Mod-97 IBAN shared across platforms",
        },
        {
            "type": "url",
            "value_norm": base_url,
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_405", "raw_value": wa_url_raw},
                {"app": "telegram", "location": "messages_v2_mid_405", "raw_value": tg_url_raw},
            ],
            "expected_link": True,
            "notes": "Identical URL destination differing in www. prefix and tracking parameters",
        },
        {
            "type": "image_near_duplicate",
            "value_norm": f"dhash_wa_{hex(wa_dhash)}_tg_{hex(tg_dhash)}",
            "occurrences": [
                {"app": "whatsapp", "location": "Media/WhatsApp Images/IMG-SHARED-001.jpg", "raw_value": "IMG-SHARED-001.jpg"},
                {"app": "telegram", "location": "Media/Telegram/PHOTO-SHARED-001.jpg", "raw_value": "PHOTO-SHARED-001.jpg"},
            ],
            "expected_link": True,
            "notes": f"Near-duplicate image pair with dHash Hamming distance = {dist_near_dup} (<= 4 threshold)",
        },
        {
            "type": "gps_rendezvous",
            "value_norm": f"mumbai_gw_distance_{r_dist:.1f}m_time_45min",
            "occurrences": [
                {"app": "whatsapp", "location": "message_location_row_406", "raw_value": "18.921984,72.834654@1789826400000"},
                {"app": "telegram", "location": "messages_v2_mid_406", "raw_value": "18.922850,72.835250@1789829100000"},
            ],
            "expected_link": True,
            "notes": f"GPS rendezvous <= 250m ({r_dist:.1f}m) and <= 2h (45m apart)",
        },
    ]

    # 7. Decoys Manifest Entries
    dist_exceeded_m = haversine_distance_m(18.921984, 72.834654, 18.925500, 72.834654)
    decoys = [
        {
            "type": "phone",
            "value_norm": "Rohan Sharma (Decoy)",
            "occurrences": [
                {"app": "whatsapp", "location": "wa.db/wa_contacts_rohan", "raw_value": "+919876540001"},
                {"app": "telegram", "location": "cache4.db/users_rohan_decoy", "raw_value": "+919876549999"},
            ],
            "expected_link": False,
            "decoy_reason": "same_display_name_different_phone",
            "notes": "Identical contact name with different phone numbers; union-find must not link above weak_hint",
        },
        {
            "type": "btc_address",
            "value_norm": btc_decoy,
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_407", "raw_value": btc_decoy},
                {"app": "telegram", "location": "messages_v2_mid_407", "raw_value": btc_decoy},
            ],
            "expected_link": False,
            "decoy_reason": "invalid_btc_checksum",
            "notes": "Similar looking BTC address with invalid Base58Check checksum; must produce 0 links",
        },
        {
            "type": "evm_address",
            "value_norm": evm_decoy,
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_408", "raw_value": evm_decoy},
                {"app": "telegram", "location": "messages_v2_mid_408", "raw_value": evm_decoy},
            ],
            "expected_link": False,
            "decoy_reason": "invalid_evm_checksum",
            "notes": "EVM address with corrupted EIP-55 casing; must produce 0 links",
        },
        {
            "type": "iban",
            "value_norm": iban_decoy,
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_409", "raw_value": iban_decoy},
                {"app": "telegram", "location": "messages_v2_mid_409", "raw_value": iban_decoy},
            ],
            "expected_link": False,
            "decoy_reason": "invalid_iban_checksum",
            "notes": "IBAN with invalid mod-97 check digits; must produce 0 links",
        },
        {
            "type": "url",
            "value_norm": "https://example.test/case-files",
            "occurrences": [
                {"app": "whatsapp", "location": "message_row_410", "raw_value": "https://example.test/case-files/folder-alpha"},
                {"app": "telegram", "location": "messages_v2_mid_410", "raw_value": "https://example.test/case-files/folder-beta"},
            ],
            "expected_link": False,
            "decoy_reason": "different_url_path",
            "notes": "Same domain host but different path segments; path remains significant so no link",
        },
        {
            "type": "image_near_duplicate",
            "value_norm": f"dhash_wa_{hex(wa_dhash)}_decoy_{hex(decoy_dhash)}",
            "occurrences": [
                {"app": "whatsapp", "location": "Media/WhatsApp Images/IMG-DECOY-DISSIMILAR.jpg", "raw_value": "IMG-DECOY-DISSIMILAR.jpg"},
                {"app": "telegram", "location": "Media/Telegram/PHOTO-SHARED-001.jpg", "raw_value": "PHOTO-SHARED-001.jpg"},
            ],
            "expected_link": False,
            "decoy_reason": "image_dissimilar",
            "notes": f"Visually dissimilar image pair with dHash distance = {dist_decoy} (>= 10 threshold)",
        },
        {
            "type": "gps_rendezvous",
            "value_norm": f"distance_exceeded_{dist_exceeded_m:.1f}m",
            "occurrences": [
                {"app": "whatsapp", "location": "message_location_row_411", "raw_value": "18.921984,72.834654@1789826400000"},
                {"app": "telegram", "location": "messages_v2_mid_411", "raw_value": f"18.925500,72.834654@{rendezvous_ts_wa + 600000}"},
            ],
            "expected_link": False,
            "decoy_reason": "rendezvous_distance_exceeded",
            "notes": f"Locations are {dist_exceeded_m:.1f}m apart (exceeds 250m threshold)",
        },
        {
            "type": "gps_rendezvous",
            "value_norm": "time_exceeded_210min",
            "occurrences": [
                {"app": "whatsapp", "location": "message_location_row_412", "raw_value": "18.921984,72.834654@1789826400000"},
                {"app": "telegram", "location": "messages_v2_mid_412", "raw_value": f"18.921984,72.834654@{rendezvous_ts_wa + 210 * 60 * 1000}"},
            ],
            "expected_link": False,
            "decoy_reason": "rendezvous_time_exceeded",
            "notes": "Same location coordinate but 210 minutes apart (exceeds 120m / 2h threshold)",
        },
        {
            "type": "gps_rendezvous",
            "value_norm": "different_cities_mumbai_delhi",
            "occurrences": [
                {"app": "whatsapp", "location": "message_location_row_413", "raw_value": "18.921984,72.834654@1789826400000"},
                {"app": "telegram", "location": "messages_v2_mid_413", "raw_value": f"28.632743,77.219597@{rendezvous_ts_wa}"},
            ],
            "expected_link": False,
            "decoy_reason": "rendezvous_different_place",
            "notes": "Same timestamp but entirely different geographic locations (~1150 km apart)",
        },
    ]

    controls = [
        {
            "name": "cross_app_correlation_ground_truth",
            "assertion": "planted_shared_entities_discoverable",
            "expected_outcome": "recall == 1.0",
        },
        {
            "name": "cross_app_decoy_rejection",
            "assertion": "decoys_rejected_above_threshold",
            "expected_outcome": "false_positive_count == 0",
        },
    ]

    # Recompute files info
    files_info: List[DatasetFileInfo] = []
    for f_path in sorted(output_dir.rglob("*")):
        if f_path.is_file() and f_path.name != "manifest.json" and "_temp" not in str(f_path):
            sha, sz = _compute_sha256(f_path)
            rel_p = str(f_path.relative_to(output_dir)).replace("\\", "/")
            files_info.append(DatasetFileInfo(path=rel_p, sha256=sha, size=sz))

    manifest = DatasetManifest(
        dataset_id=dataset_id,
        variant=variant,
        seed=seed,
        generator_version="1.0.0",
        origin="synthetic",
        created_by_tool_versions={
            "python": sys.version.split()[0],
            "sqlite3": sqlite3.sqlite_version,
            "pillow": "12.3.0",
            "telethon": "1.45.0",
        },
        files=files_info,
        whatsapp=wa_manifest.whatsapp,
        telegram=tg_manifest.telegram,
        shared_entities=shared_entities,
        decoys=decoys,
        controls=controls,
        modelled_vs_observed={
            "whatsapp_schema": "modelled",
            "telegram_tl_blobs": "modelled",
            "cross_app_links": "modelled",
        },
    )
    manifest.save(output_dir / "manifest.json")
    return manifest


# =============================================================================
# B4.2 / DS-07: Control Dataset Generator (Unrelated Device, 0 Shared Entities)
# =============================================================================

def generate_control_dataset(
    output_dir: Path,
    dataset_id: str = "DS-07",
    variant: str = "dev",
    seed: Optional[int] = None,
) -> DatasetManifest:
    """Generate the control ground-truth dataset (DS-07)."""
    if seed is None:
        seed = 20261017 if variant == "dev" else 7102603

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean existing
    for p in output_dir.glob("*"):
        if p.is_file():
            p.unlink()

    wa_manifest = generate_whatsapp_plain_dataset(
        output_dir=output_dir,
        dataset_id=dataset_id,
        variant=variant,
        seed=seed + 500,
    )

    tg_manifest = generate_telegram_dataset(
        output_dir=output_dir,
        dataset_id=dataset_id,
        variant=variant,
        seed=seed + 600,
    )

    controls = [
        {
            "name": "zero_shared_entities_control",
            "assertion": "no_shared_phones_wallets_urls_or_rendezvous",
            "expected_outcome": "findings_count == 0",
        },
        {
            "name": "control_fpr_benchmark",
            "assertion": "unrelated_device_produces_no_correlation_above_threshold",
            "expected_outcome": "fpr == 0.0",
        },
    ]

    files_info: List[DatasetFileInfo] = []
    for f_path in sorted(output_dir.rglob("*")):
        if f_path.is_file() and f_path.name != "manifest.json" and "_temp" not in str(f_path):
            sha, sz = _compute_sha256(f_path)
            rel_p = str(f_path.relative_to(output_dir)).replace("\\", "/")
            files_info.append(DatasetFileInfo(path=rel_p, sha256=sha, size=sz))

    manifest = DatasetManifest(
        dataset_id=dataset_id,
        variant=variant,
        seed=seed,
        generator_version="1.0.0",
        origin="synthetic",
        created_by_tool_versions={
            "python": sys.version.split()[0],
            "sqlite3": sqlite3.sqlite_version,
            "pillow": "12.3.0",
            "telethon": "1.45.0",
        },
        files=files_info,
        whatsapp=wa_manifest.whatsapp,
        telegram=tg_manifest.telegram,
        shared_entities=[],
        decoys=[],
        controls=controls,
        modelled_vs_observed={
            "whatsapp_schema": "modelled",
            "telegram_tl_blobs": "modelled",
            "control_unrelated_device": "modelled",
        },
    )
    manifest.save(output_dir / "manifest.json")
    return manifest


# =============================================================================
# B4 / DS-08: Tamper Dataset Generator (1-Byte Flips at Recorded Offsets)
# =============================================================================

def generate_tamper_dataset(
    output_dir: Path,
    dataset_id: str = "DS-08",
    variant: str = "dev",
    seed: Optional[int] = None,
) -> DatasetManifest:
    """Generate the tamper ground-truth dataset (DS-08)."""
    if seed is None:
        seed = 20261018 if variant == "dev" else 8102604

    rng = DeterministicRNG(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_db_path = output_dir / "reference_base.db"
    conn = sqlite3.connect(base_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA page_size = 4096")
    cur.execute("CREATE TABLE evidence_sample (id INTEGER PRIMARY KEY, marker TEXT, payload BLOB)")
    for i in range(1, 51):
        cur.execute(
            "INSERT INTO evidence_sample VALUES (?, ?, ?)",
            (i, f"MARKER_{i:04d}_{rng.unique_marker('SMP')}", rng.random_bytes(128)),
        )
    conn.commit()
    conn.close()

    base_bytes = base_db_path.read_bytes()
    orig_sha256 = hashlib.sha256(base_bytes).hexdigest()
    file_len = len(base_bytes)

    fixed_offsets = [0, 15, 16, 100, 512, 1024, 2048, 4095, file_len - 1]
    random_offsets = [rng.randint(101, file_len - 2) for _ in range(15)]
    all_offsets = sorted(list(set(fixed_offsets + random_offsets)))

    tamper_records: List[Dict[str, Any]] = []
    files_info: List[DatasetFileInfo] = [
        DatasetFileInfo(path="reference_base.db", sha256=orig_sha256, size=file_len)
    ]

    for idx, offset in enumerate(all_offsets, start=1):
        mutated = bytearray(base_bytes)
        orig_b = mutated[offset]
        flipped_b = orig_b ^ 0x55
        mutated[offset] = flipped_b

        mut_bytes = bytes(mutated)
        mut_sha = hashlib.sha256(mut_bytes).hexdigest()
        assert mut_sha != orig_sha256, f"SHA-256 did not change on byte flip at offset {offset}"

        fixture_name = f"tampered_offset_{offset:06d}.db"
        fixture_path = output_dir / fixture_name
        fixture_path.write_bytes(mut_bytes)

        files_info.append(DatasetFileInfo(path=fixture_name, sha256=mut_sha, size=len(mut_bytes)))
        tamper_records.append({
            "fixture_path": fixture_name,
            "original_sha256": orig_sha256,
            "tampered_sha256": mut_sha,
            "flip_offset": offset,
            "original_byte": orig_b,
            "flipped_byte": flipped_b,
            "description": f"Single-byte flip at offset {offset} ({orig_b} -> {flipped_b})",
        })

    controls = [
        {
            "name": "tamper_detection_rate",
            "assertion": "every_single_byte_mutation_detected",
            "expected_outcome": "detection_rate == 1.0",
        }
    ]

    manifest = DatasetManifest(
        dataset_id=dataset_id,
        variant=variant,
        seed=seed,
        generator_version="1.0.0",
        origin="synthetic",
        created_by_tool_versions={
            "python": sys.version.split()[0],
            "sqlite3": sqlite3.sqlite_version,
        },
        files=files_info,
        whatsapp=None,
        telegram=None,
        shared_entities=[],
        decoys=[],
        controls=controls,
        tamper_records=tamper_records,
        modelled_vs_observed={
            "sqlite_tamper_mutations": "modelled",
        },
    )
    manifest.save(output_dir / "manifest.json")
    return manifest
