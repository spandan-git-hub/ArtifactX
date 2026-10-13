"""Unit tests for configuration and documentation consistency (Section A7)."""

from pathlib import Path
import pytest
from backend.app.config import Settings, settings

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.mark.unit
def test_config_settings_defaults():
    """Verify backend settings match Section A7 requirements and DEC-009."""
    assert settings.max_upload_size == 268435456  # 256 MiB in bytes
    assert hasattr(settings, "test_database_url")
    assert settings.test_database_url == "sqlite+pysqlite:///:memory:"

    # Verify class defaults without env file
    default_settings = Settings(_env_file=None)
    assert default_settings.max_upload_size == 268435456
    assert default_settings.test_database_url == "sqlite+pysqlite:///:memory:"

    # Verify deleted legacy settings do not exist
    assert not hasattr(settings, "upload_dir")
    assert not hasattr(settings, "demo_mode")


@pytest.mark.unit
def test_env_example_content():
    """Verify .env.example contains correct placeholders and no deprecated settings."""
    env_example_path = ROOT_DIR / ".env.example"
    assert env_example_path.is_file(), ".env.example must exist"

    content = env_example_path.read_text(encoding="utf-8")

    # Required variables
    assert "DATABASE_URL=" in content
    assert "TEST_DATABASE_URL=" in content
    assert "MAX_UPLOAD_SIZE=268435456" in content
    assert "LOG_LEVEL=" in content
    assert "DEBUG=" in content

    # Deprecated/forbidden variables
    assert "UPLOAD_DIR" not in content
    assert "DEMO_MODE" not in content

    # Memory documentation
    assert "memory" in content.lower()


@pytest.mark.unit
def test_reportbysonnet_marked_superseded():
    """Verify REPORTBYSONNET.md has header marking it superseded."""
    report_path = ROOT_DIR / "REPORTBYSONNET.md"
    assert report_path.is_file(), "REPORTBYSONNET.md must exist"

    lines = report_path.read_text(encoding="utf-8").splitlines()[:15]
    header_text = "\n".join(lines)

    assert "SUPERSEDED" in header_text
    assert "PROJECT_STATE.md" in header_text
    assert "AUDIT_A0.md" in header_text


@pytest.mark.unit
def test_project_state_doc_exists():
    """Verify docs/PROJECT_STATE.md exists and describes the current post-cleanup state."""
    state_path = ROOT_DIR / "docs" / "PROJECT_STATE.md"
    assert state_path.is_file(), "docs/PROJECT_STATE.md must exist"

    content = state_path.read_text(encoding="utf-8")
    assert "Phase A (Required Cleanup) Complete" in content
    assert "Zero runtime disk writes" in content
    assert "DECRYPTOR_NOT_AVAILABLE" in content
    assert "LEGACY_UNVERIFIABLE" in content


@pytest.mark.unit
def test_limitations_doc_exists():
    """Verify docs/LIMITATIONS.md exists and documents all required forensic boundaries."""
    limitations_path = ROOT_DIR / "docs" / "LIMITATIONS.md"
    assert limitations_path.is_file(), "docs/LIMITATIONS.md must exist"

    content = limitations_path.read_text(encoding="utf-8")
    assert "No Key-Less Decryption" in content
    assert "64-character hexadecimal" in content or "64-hex" in content
    assert "Secret Chats" in content
    assert "MTProto" in content
    assert "ID Sequence Gaps" in content or "ID sequence gaps" in content
    assert "weak_hint" in content or "weak indicator" in content
    assert "Synthetic-Fixture Validation" in content or "synthetic ground-truth" in content
    assert "tdata" in content
    assert "iOS" in content
    assert "Section 63 BSA" in content
    assert "Device Clock" in content or "clock" in content
