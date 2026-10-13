"""Unit tests for Section A4 — Verification of banned language removal (R9 / P2-B).

Verifies:
1. tools/guards/banned_language.py passes cleanly across the entire workspace (0 violations).
2. Guard accurately detects all banned terminology (court-ready, sworn, legally admissible, etc.) in a synthetic file.
3. Inline comments ('guard:allow-banned-language', '<!-- guard:allow-banned-term-table -->') are respected.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.guards import banned_language


def test_banned_language_guard_passes_on_repo():
    """Verify banned_language guard reports zero violations on the workspace."""
    exit_code = banned_language.run()
    assert exit_code == 0, "banned_language guard detected un-sanitized banned terminology"


def test_banned_language_guard_detects_violations(tmp_path):
    """Verify guard detects all R9 banned terms (mutation check)."""
    bad_file = tmp_path / "bad_language_sample.py"
    bad_file.write_text(
        "doc = 'court-ready report'\n"
        "status = 'legally admissible'\n"
        "result = 'admissible in court'\n"
        "claim = 'proves authenticity'\n"
        "statement = 'proof of integrity'\n"
        "sla = 'guaranteed delivery'\n"
        "storage = 'tamper-proof ledger'\n"
        "crypto = 'decrypts without key'\n"
        "analyst = 'sworn officer'\n"
        "mode = 'demo mode active'\n",
        encoding="utf-8"
    )

    violations = banned_language.scan_file(bad_file)
    assert len(violations) == 10, f"Expected 10 violations, got {len(violations)}: {violations}"
    terms_detected = {term for _, term, _ in violations}
    assert "court-ready / court ready" in terms_detected
    assert "legally admissible" in terms_detected
    assert "admissible in court" in terms_detected
    assert "proves" in terms_detected
    assert "proof of" in terms_detected
    assert "guaranteed" in terms_detected
    assert "tamper-proof" in terms_detected
    assert "decrypts without key" in terms_detected
    assert "sworn" in terms_detected
    assert "demo mode" in terms_detected


def test_banned_language_inline_exemptions(tmp_path):
    """Verify inline guard comments allow specified lines."""
    exempt_file = tmp_path / "exempt_language_sample.py"
    exempt_file.write_text(
        "court_ready = True  # guard:allow-banned-language\n"
        "<!-- guard:allow-banned-term-table -->\n"
        "sworn_statement = 'exempt'\n",
        encoding="utf-8"
    )

    violations = banned_language.scan_file(exempt_file)
    assert len(violations) == 0, f"Expected 0 violations with guard:allow, got {violations}"
