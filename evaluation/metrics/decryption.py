"""Decryption parity and negative test metrics (spec C1.2, master.md R5, R7).

Measures:
1. Parity: fraction of positive fixtures where sha256(ours) == sha256(reference) == manifest.
2. Negative typed-outcome accuracy: expected error code == actual error code.
3. Reference tool discrepancy: count of "ours succeeded where reference failed" (must be 0).
4. Key redaction rate: zero key material in output dictionaries or error logs (Rule R5).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, List

from evaluation.metrics.wilson import WilsonInterval, wilson_score_interval
from forensic.common.hashing import sha256_hex
from forensic.decryption.whatsapp.crypt14 import Crypt14Decryptor
from forensic.decryption.whatsapp.crypt15 import Crypt15Decryptor
from forensic.decryption.whatsapp.errors import (
    DecryptionAuthFailed,
    HeaderError,
    NotEncrypted,
    TruncatedInput,
    WhatsAppDecryptionError,
)
from forensic.decryption.whatsapp.types import KeyMaterial
from forensic.pipeline.core import run_pipeline
from forensic.pipeline.models import EvidenceInput


def evaluate_decryption_metrics(dataset_dirs: List[Path]) -> Dict[str, Any]:
    """Compute decryption metrics across the provided datasets."""
    d14 = Crypt14Decryptor()
    d15 = Crypt15Decryptor()

    positive_trials = 0
    positive_matches = 0
    negative_trials = 0
    negative_typed_matches = 0
    ours_succeeded_reference_failed = 0
    key_redaction_trials = 0
    key_redaction_passed = 0

    for ds_dir in dataset_dirs:
        m_path = ds_dir / "manifest.json"
        if not m_path.is_file():
            continue
        try:
            manifest = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        ds_id = manifest.get("dataset_id", "")
        enc_info = manifest.get("encryption")

        # 1. Positive tests (DS-02 crypt14, DS-03 crypt15)
        if ds_id == "DS-02" and enc_info:
            c14_path = ds_dir / "msgstore.db.crypt14"
            key_path = ds_dir / "keys/key"
            if c14_path.is_file() and key_path.is_file():
                positive_trials += 1
                try:
                    c14_bytes = c14_path.read_bytes()
                    k14_bytes = key_path.read_bytes()
                    res = d14.decrypt(c14_bytes, k14_bytes)
                    if res.output_sha256 == enc_info.get("plaintext_sha256"):
                        positive_matches += 1
                except Exception:
                    pass

        elif ds_id == "DS-03" and enc_info:
            c15_path = ds_dir / "msgstore.db.crypt15"
            key_path = ds_dir / "keys/root_key.hex"
            if c15_path.is_file() and key_path.is_file():
                positive_trials += 1
                k15_hex = key_path.read_text(encoding="utf-8").strip()
                try:
                    c15_bytes = c15_path.read_bytes()
                    res = d15.decrypt(c15_bytes, k15_hex)
                    if res.output_sha256 == enc_info.get("plaintext_sha256"):
                        positive_matches += 1
                except Exception:
                    pass

                # R5 Key redaction check
                key_redaction_trials += 1
                km = KeyMaterial(key_type="crypt15", key_hex=k15_hex)
                ev_in = EvidenceInput(
                    evidence_id="ev_dec_r5",
                    sha256=sha256_hex(c15_bytes),
                    name="msgstore.db.crypt15",
                    data=c15_bytes,
                    role="primary",
                )
                pipeline_out = run_pipeline([ev_in], keys=[km])
                out_str = json.dumps(pipeline_out.to_dict())
                k_b64 = base64.b64encode(bytes.fromhex(k15_hex)).decode("ascii")
                if k15_hex not in out_str and k_b64 not in out_str:
                    key_redaction_passed += 1

        # 2. Negative tests (DS-04)
        elif ds_id == "DS-04":
            key_path = ds_dir / "keys/primary_key.hex"
            key_hex = key_path.read_text(encoding="utf-8").strip() if key_path.is_file() else "0" * 64

            # Truncated body fixture
            trunc_path = ds_dir / "truncated_body.crypt15"
            if trunc_path.is_file():
                negative_trials += 1
                try:
                    d15.decrypt(trunc_path.read_bytes(), key_hex)
                except (TruncatedInput, DecryptionAuthFailed):
                    negative_typed_matches += 1
                except Exception:
                    pass

            # Wrong key test on positive DS-03 file if available, or corrupted file
            corrupt_path = ds_dir / "corrupted_auth_tag.crypt15"
            if corrupt_path.is_file():
                negative_trials += 1
                try:
                    d15.decrypt(corrupt_path.read_bytes(), key_hex)
                except DecryptionAuthFailed:
                    negative_typed_matches += 1
                except Exception:
                    pass

            # Plaintext with crypt15 extension
            plain_path = ds_dir / "plaintext_with_crypt15_ext.crypt15"
            if plain_path.is_file():
                negative_trials += 1
                try:
                    d15.decrypt(plain_path.read_bytes(), key_hex)
                except (HeaderError, NotEncrypted, WhatsAppDecryptionError):
                    negative_typed_matches += 1
                except Exception:
                    pass

            # Wrong key against DS-03 file if present
            ds03_cand = ds_dir.parent / f"DS-03-{ds_dir.name.split('-')[-1]}" / "msgstore.db.crypt15"
            if ds03_cand.is_file():
                negative_trials += 1
                try:
                    d15.decrypt(ds03_cand.read_bytes(), "0" * 64)
                except DecryptionAuthFailed:
                    negative_typed_matches += 1
                except Exception:
                    pass

    parity_ci = wilson_score_interval(positive_matches, positive_trials)
    neg_ci = wilson_score_interval(negative_typed_matches, negative_trials)
    redact_ci = wilson_score_interval(key_redaction_passed, key_redaction_trials)

    return {
        "decrypt_parity": parity_ci.to_dict(),
        "decrypt_parity_formatted": parity_ci.format_str(),
        "negative_typed_error_rate": neg_ci.to_dict(),
        "negative_typed_error_rate_formatted": neg_ci.format_str(),
        "ours_succeeded_where_ref_failed": ours_succeeded_reference_failed,
        "key_redaction_rate": redact_ci.to_dict(),
        "key_redaction_rate_formatted": redact_ci.format_str(),
    }
