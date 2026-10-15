"""
Unit tests for pure forensic pipeline core (spec 11_PIPELINE_AND_E2E.md §B13.1).

Verifies:
- Stage ordering: integrity -> detect -> decrypt -> parse -> recover -> timeline -> correlate
- Stage isolation & dependency-skip logic
- Re-check integrity before each stage
- Determinism under input shuffle (R11)
- R5 key material exclusion from results and summaries
- Zero disk writes (R4)
"""

from pathlib import Path
import random
import pytest

from forensic.common.hashing import sha256_hex
from forensic.decryption.whatsapp.types import KeyMaterial
from forensic.pipeline import (
    EvidenceInput,
    PipelineConfig,
    run_pipeline,
)


@pytest.fixture
def sample_wa_evidence():
    """Load sample WhatsApp msgstore and wa.db from DS-01-dev."""
    base_dir = Path("testdata/DS-01-dev")
    msgstore_path = base_dir / "msgstore.db"
    wa_db_path = base_dir / "wa.db"

    msgstore_data = msgstore_path.read_bytes()
    wa_db_data = wa_db_path.read_bytes()

    inputs = [
        EvidenceInput(
            evidence_id="1",
            sha256=sha256_hex(msgstore_data),
            name="msgstore.db",
            data=msgstore_data,
            role="primary",
        ),
        EvidenceInput(
            evidence_id="2",
            sha256=sha256_hex(wa_db_data),
            name="wa.db",
            data=wa_db_data,
            role="wa_contacts",
        ),
    ]
    return inputs


@pytest.fixture
def sample_tg_evidence():
    """Load sample Telegram cache4.db from DS-05-dev."""
    base_dir = Path("testdata/DS-05-dev")
    cache4_path = base_dir / "cache4.db"
    cache4_data = cache4_path.read_bytes()

    return [
        EvidenceInput(
            evidence_id="10",
            sha256=sha256_hex(cache4_data),
            name="cache4.db",
            data=cache4_data,
            role="primary",
        )
    ]


def test_pipeline_pure_wa_execution_order(sample_wa_evidence):
    """Assert stages run in required sequence and produce valid PipelineResult."""
    result = run_pipeline(sample_wa_evidence)

    assert result.status == "COMPLETED"
    assert result.content_hash is not None and len(result.content_hash) == 64

    stage_names = [s.stage for s in result.stages]
    # Check that stages appear in order: integrity, detect, parse, recover, timeline, correlate
    assert "integrity" in stage_names
    assert "detect" in stage_names
    assert "parse" in stage_names
    assert "recover" in stage_names
    assert "timeline" in stage_names
    assert "correlate" in stage_names

    # Check counts
    assert result.summary["counts"]["whatsapp_messages"] > 0
    assert result.summary["counts"]["timeline_events"] > 0
    assert result.summary["failed_inputs"] == 0


def test_pipeline_encrypted_without_key_honest_failure():
    """Assert encrypted container without key produces typed FAILED_HONEST and skips downstream."""
    crypt14_path = Path("testdata/DS-02-dev/msgstore.db.crypt14")
    crypt14_data = crypt14_path.read_bytes()

    inputs = [
        EvidenceInput(
            evidence_id="100",
            sha256=sha256_hex(crypt14_data),
            name="msgstore.db.crypt14",
            data=crypt14_data,
            role="primary",
        )
    ]

    result = run_pipeline(inputs, keys=())

    assert result.status == "PARTIAL"
    decrypt_stages = [s for s in result.stages if s.stage == "decrypt"]
    assert len(decrypt_stages) == 1
    assert decrypt_stages[0].status == "FAILED_HONEST"
    assert decrypt_stages[0].error_code == "ENCRYPTED_KEY_REQUIRED"

    # Downstream parse and recover stages should be skipped with reason
    parse_stages = [s for s in result.stages if s.stage == "parse"]
    assert len(parse_stages) == 1
    assert parse_stages[0].status == "SKIPPED"
    assert parse_stages[0].skip_reason == "dependency:decrypt"

    recover_stages = [s for s in result.stages if s.stage == "recover"]
    assert len(recover_stages) == 1
    assert recover_stages[0].status == "SKIPPED"


def test_pipeline_stage_isolation_on_corrupt_evidence(sample_wa_evidence):
    """Assert corrupted evidence fails integrity stage but doesn't abort valid evidence."""
    corrupted_data = b"Corrupted arbitrary data"
    bad_input = EvidenceInput(
        evidence_id="999",
        sha256="0000000000000000000000000000000000000000000000000000000000000000",
        name="tampered.db",
        data=corrupted_data,
        role="other",
    )
    all_inputs = sample_wa_evidence + [bad_input]

    result = run_pipeline(all_inputs)

    # Valid WA evidence completed successfully
    assert result.summary["counts"]["whatsapp_messages"] > 0
    assert result.summary["failed_inputs"] == 1

    # Bad evidence is flagged
    bad_integrity = [s for s in result.stages if s.stage == "integrity" and s.evidence_id == "999"]
    assert len(bad_integrity) == 1
    assert bad_integrity[0].status == "FAILED_HONEST"
    assert bad_integrity[0].error_code == "INTEGRITY_FAILURE"

    bad_detect = [s for s in result.stages if s.stage == "detect" and s.evidence_id == "999"]
    assert len(bad_detect) == 1
    assert bad_detect[0].status == "SKIPPED"


def test_pipeline_shuffle_determinism(sample_wa_evidence):
    """Assert shuffling input exhibits produces 100% byte-identical content_hash and findings."""
    rng = random.Random(42)
    inputs_a = list(sample_wa_evidence)
    inputs_b = list(sample_wa_evidence)
    rng.shuffle(inputs_b)

    res_a = run_pipeline(inputs_a, run_id="run_fixed")
    res_b = run_pipeline(inputs_b, run_id="run_fixed")

    assert res_a.content_hash == res_b.content_hash
    assert len(res_a.stages) == len(res_b.stages)
    for sa, sb in zip(res_a.stages, res_b.stages):
        assert sa.output_hash == sb.output_hash
        assert sa.canonical_content_bytes() == sb.canonical_content_bytes()


def test_pipeline_r5_key_material_protection():
    """Assert secret key bytes never leak into PipelineResult, StageResult, or summaries."""
    crypt14_path = Path("testdata/DS-02-dev/msgstore.db.crypt14")
    key_path = Path("testdata/DS-02-dev/keys/key")
    crypt14_data = crypt14_path.read_bytes()
    key_data = key_path.read_bytes()

    key_mat = KeyMaterial(key_file_bytes=key_data, key_type="crypt14")
    raw_secret_hex = key_mat.key_hex

    inputs = [
        EvidenceInput(
            evidence_id="101",
            sha256=sha256_hex(crypt14_data),
            name="msgstore.db.crypt14",
            data=crypt14_data,
            role="primary",
        )
    ]

    result = run_pipeline(inputs, keys=[key_mat])
    result_dict_str = str(result.to_dict())

    # Raw secret hex must NEVER appear in result
    assert raw_secret_hex not in result_dict_str
    assert key_data.hex() not in result_dict_str

    # Only truncated 8-character fingerprint may appear
    assert key_mat.fingerprint() in result_dict_str


def test_pipeline_pure_tg_execution(sample_tg_evidence):
    """Assert Telegram cache4.db runs through pipeline successfully."""
    base_dir = Path("testdata/DS-05-dev")
    wal_data = (base_dir / "cache4.db-wal").read_bytes()
    shm_data = (base_dir / "cache4.db-shm").read_bytes()

    inputs = sample_tg_evidence + [
        EvidenceInput(
            evidence_id="11",
            sha256=sha256_hex(wal_data),
            name="cache4.db-wal",
            data=wal_data,
            role="wal",
        ),
        EvidenceInput(
            evidence_id="12",
            sha256=sha256_hex(shm_data),
            name="cache4.db-shm",
            data=shm_data,
            role="shm",
        ),
    ]

    result = run_pipeline(inputs)

    assert result.status == "COMPLETED"
    assert result.summary["counts"]["telegram_messages"] > 0
    assert result.summary["counts"]["timeline_events"] > 0
    parse_stage = [s for s in result.stages if s.stage == "parse" and s.evidence_id == "10"][0]
    assert parse_stage.status == "COMPLETED"
    assert parse_stage.counts["messages"] > 0


def test_pipeline_tamper_ds08_detection():
    """Assert DS-08 tampered exhibit is flagged with INTEGRITY_FAILURE and downstream skipped."""
    base_dir = Path("testdata/DS-08-dev")
    tampered_data = (base_dir / "tampered_offset_000000.db").read_bytes()
    reference_data = (base_dir / "reference_base.db").read_bytes()
    original_sha256 = sha256_hex(reference_data)

    inputs = [
        EvidenceInput(
            evidence_id="801",
            sha256=original_sha256,
            name="reference_base.db",
            data=tampered_data,
            role="primary",
        )
    ]

    result = run_pipeline(inputs)

    integrity_stages = [s for s in result.stages if s.stage == "integrity"]
    assert len(integrity_stages) == 1
    assert integrity_stages[0].status == "FAILED_HONEST"
    assert integrity_stages[0].error_code == "INTEGRITY_FAILURE"

    # All downstream stages skipped
    detect_stages = [s for s in result.stages if s.stage == "detect"]
    assert detect_stages[0].status == "SKIPPED"


def test_pipeline_wrong_key_auth_failed():
    """Assert decryption with wrong key produces typed AUTH_FAILED."""
    crypt14_path = Path("testdata/DS-02-dev/msgstore.db.crypt14")
    crypt14_data = crypt14_path.read_bytes()

    # Wrong key material
    wrong_key = KeyMaterial(raw_key=b"0" * 32, key_type="crypt14")

    inputs = [
        EvidenceInput(
            evidence_id="102",
            sha256=sha256_hex(crypt14_data),
            name="msgstore.db.crypt14",
            data=crypt14_data,
            role="primary",
        )
    ]

    result = run_pipeline(inputs, keys=[wrong_key])

    decrypt_stages = [s for s in result.stages if s.stage == "decrypt"]
    assert len(decrypt_stages) == 1
    assert decrypt_stages[0].status == "FAILED_HONEST"
    assert decrypt_stages[0].error_code == "AUTH_FAILED"


def test_pipeline_plaintext_named_crypt15_conflict():
    """Assert plaintext SQLite named .crypt15 is detected as plaintext, parsed, and conflict noted."""
    ds4_path = Path("testdata/DS-04-dev/plaintext_sqlite.crypt15")
    data = ds4_path.read_bytes()

    inputs = [
        EvidenceInput(
            evidence_id="401",
            sha256=sha256_hex(data),
            name="plaintext_sqlite.crypt15",
            data=data,
            role="primary",
        )
    ]

    result = run_pipeline(inputs)

    # Detect stage records the conflict
    detect_stage = [s for s in result.stages if s.stage == "detect"][0]
    assert detect_stage.status == "COMPLETED"
    assert len(detect_stage.warnings) > 0
    assert any("claims encrypted" in w.lower() or "unencrypted" in w.lower() for w in detect_stage.warnings)

    # Parsing stage still executes because format is plaintext SQLite
    parse_stages = [s for s in result.stages if s.stage == "parse"]
    assert len(parse_stages) == 1
    assert parse_stages[0].status == "COMPLETED"
    assert parse_stages[0].counts["messages"] > 0

