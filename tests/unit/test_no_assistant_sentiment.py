"""Unit tests for Section A3 — Verification of assistant and sentiment remnants removal.

Verifies:
1. /api/assistant endpoints are absent (returns 404) and no registered route contains assistant/sentiment/copilot.
2. tools/guards/no_assistant_sentiment.py passes cleanly on the workspace (0 violations).
3. Guard accurately detects injected violations (mutation check) and respects guard:allow comments.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from tools.guards import no_assistant_sentiment


def test_no_assistant_endpoints_exist():
    """Verify assistant and sentiment endpoints are not registered in the application router."""
    client = TestClient(app)
    # Check legacy assistant route paths return 404 Not Found
    assert client.get("/api/assistant").status_code == 404
    assert client.post("/api/assistant").status_code == 404
    assert client.post("/api/assistant/chat").status_code == 404
    assert client.get("/api/sentiment").status_code == 404

    # Verify no registered router path contains 'assistant', 'sentiment', or 'copilot'
    registered_paths = [getattr(r, "path", "") for r in app.routes]
    banned_paths = [
        p for p in registered_paths
        if any(term in p.lower() for term in ("assistant", "sentiment", "copilot"))
    ]
    assert banned_paths == [], f"Found unexpected assistant/sentiment routes: {banned_paths}"


def test_no_assistant_sentiment_guard_passes_on_repo():
    """Verify no_assistant_sentiment guard runs clean on the current repository tree."""
    exit_code = no_assistant_sentiment.run()
    assert exit_code == 0, "no_assistant_sentiment guard found unexpected remnants in codebase"


def test_no_assistant_sentiment_guard_detects_violations(tmp_path):
    """Verify guard detects assistant/sentiment/copilot strings and respects exemptions (mutation check)."""
    # File with violations
    bad_file = tmp_path / "bad_assistant_file.py"
    bad_file.write_text(
        "class ForensicAssistantDrawer:\n"
        "    sentiment_score = 0.85\n"
        "    useAiAssistant = True\n"
        "    copilot_mode = 'active'\n",
        encoding="utf-8"
    )
    violations = no_assistant_sentiment.scan_file(bad_file)
    assert len(violations) == 4, f"Expected 4 violations, got: {violations}"

    # File with inline guard:allow exemption
    clean_file = tmp_path / "clean_assistant_file.py"
    clean_file.write_text(
        "assistant_ref = 'legacy'  # guard:allow\n"
        "sentiment_val = 0.0  # guard:allow\n",
        encoding="utf-8"
    )
    violations_clean = no_assistant_sentiment.scan_file(clean_file)
    assert len(violations_clean) == 0, f"Expected 0 violations, got: {violations_clean}"
