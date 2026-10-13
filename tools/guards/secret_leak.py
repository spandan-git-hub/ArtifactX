"""Guard against credential and secret leaks (R5, R14, A1.3).

Checks:
1. .env must never be tracked in git.
2. Hardcoded database credentials with non-placeholder passwords.
3. 64-hex key literals outside tests/ and testdata/.
4. Private key PEM headers outside tests/ and testdata/.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Matches postgres URLs with non-placeholder credentials
POSTGRES_CRED_REGEX = re.compile(
    r"postgresql(\+[a-z0-9]+)?://(?!artifactx:artifactx_password)(?!username:password)(?!user:password)(?!user:pass)(?!\$)[^:\s/]+:(?!\$)[^@\s/]+@[^/\s]+",
    re.IGNORECASE,
)

# 64-hex string literal in quotes
HEX_64_REGEX = re.compile(r"""['"][0-9a-fA-F]{64}['"]""")

# Private key PEM header
PEM_PRIVATE_KEY_REGEX = re.compile(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----")

EXCLUDED_HEX_DIRS = {"tests", "testdata", "alembic"}


def check_git_tracked_env() -> list[str]:
    violations = []
    try:
        output = subprocess.check_output(
            ["git", "ls-files", ".env"], cwd=str(ROOT_DIR), text=True, encoding="utf-8"
        ).strip()
        if output:
            violations.append((".env:1", "CRITICAL: .env file is tracked in git!"))
    except Exception:
        pass
    return violations


def scan_file(file_path: Path, rel_path: str) -> list[tuple[int, str]]:
    violations = []
    first_part = rel_path.split("/")[0]

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    for line_num, line in enumerate(content.splitlines(), start=1):
        if "guard:allow-secret" in line:
            continue

        # Check DB credentials
        if POSTGRES_CRED_REGEX.search(line):
            violations.append((line_num, "Hardcoded PostgreSQL credentials detected"))

        # Check PEM private keys
        if first_part not in EXCLUDED_HEX_DIRS and PEM_PRIVATE_KEY_REGEX.search(line):
            violations.append((line_num, "Private key PEM block header detected"))

        # Check 64-hex literals outside tests/testdata/alembic
        if first_part not in EXCLUDED_HEX_DIRS:
            if HEX_64_REGEX.search(line):
                # Check if it's a known placeholder or regex pattern
                if "0123456789abcdef" not in line and "0" * 64 not in line:
                    violations.append((line_num, "64-hex literal detected outside tests/testdata"))

    return violations


def run() -> int:
    total_violations = 0

    # 1. Check if .env is tracked
    env_violations = check_git_tracked_env()
    for loc, reason in env_violations:
        total_violations += 1
        print(f"{loc}: {reason}")

    # 2. Get git tracked files to scan
    try:
        output = subprocess.check_output(
            ["git", "ls-files"], cwd=str(ROOT_DIR), text=True, encoding="utf-8"
        )
        files = output.splitlines()
    except Exception:
        files = []
        for root, _, filenames in os.walk(str(ROOT_DIR)):
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), str(ROOT_DIR))
                files.append(rel.replace("\\", "/"))

    for rel in files:
        rel_norm = rel.replace("\\", "/")
        full_path = ROOT_DIR / rel_norm
        if not full_path.is_file():
            continue
        # Skip binary / media files
        if any(rel_norm.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".ico", ".db", ".lock")):
            continue

        file_violations = scan_file(full_path, rel_norm)
        for lineno, reason in file_violations:
            total_violations += 1
            print(f"{rel_norm}:{lineno}: {reason}")

    if total_violations > 0:
        print(f"\n[FAIL] secret_leak guard found {total_violations} violation(s).")
        return 1
    print("[PASS] secret_leak guard found 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
