"""Unit tests for Section A2 — Verification of demo seeding removal.

Verifies:
1. /api/health endpoint returns clean status without demo_mode.
2. /api/demo endpoint is absent (returns 404) and no route contains demo/seed.
3. tools/guards/no_demo_seed.py passes on the workspace and catches simulated violations.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app, health_check
from tools.guards import no_demo_seed


def test_health_check_function_direct():
    """Verify health_check() function directly returns clean payload without demo_mode."""
    data = health_check()
    assert data["status"] == "ok"
    assert "version" in data
    assert "demo_mode" not in data
    assert "demo" not in data
    assert "seed" not in data


def test_health_check_endpoint_via_client():
    """Verify GET /api/health endpoint via HTTP client returns clean payload without demo_mode."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "version" in data
    assert "demo_mode" not in data
    assert "demo" not in data
    assert "seed" not in data


def test_no_demo_endpoints_exist():
    """Verify demo endpoints are not registered in the application router."""
    client = TestClient(app)
    # Check common legacy demo route patterns return 404 Not Found
    assert client.get("/api/demo").status_code == 404
    assert client.post("/api/demo").status_code == 404
    assert client.post("/api/demo/seed").status_code == 404

    # Verify no registered router path contains 'demo' or 'seed'
    registered_paths = [getattr(r, "path", "") for r in app.routes]
    demo_paths = [p for p in registered_paths if "demo" in p.lower() or "seed" in p.lower()]
    assert demo_paths == [], f"Found unexpected demo/seed routes: {demo_paths}"


def test_no_demo_seed_guard_passes_on_repo():
    """Verify no_demo_seed guard runs clean on the current repository tree."""
    exit_code = no_demo_seed.run()
    assert exit_code == 0, "no_demo_seed guard found unexpected demo/seed remnants in codebase"


def test_no_demo_seed_guard_detects_violations(tmp_path):
    """Verify guard detects demo/seed strings and correctly respects exemptions (mutation check)."""
    # File with violations
    bad_file = tmp_path / "bad_file.py"
    bad_file.write_text("DEMO_MODE = True\ndef seed_database(): pass\n", encoding="utf-8")
    violations = no_demo_seed.scan_file(bad_file)
    assert len(violations) == 2, f"Expected 2 violations, got: {violations}"

    # File with technical exemption (random seed and inline guard:allow)
    clean_file = tmp_path / "clean_file.py"
    clean_file.write_text("rng = random.Random(random seed)\ndemo = 1  # guard:allow\n", encoding="utf-8")
    violations_clean = no_demo_seed.scan_file(clean_file)
    assert len(violations_clean) == 0, f"Expected 0 violations, got: {violations_clean}"
