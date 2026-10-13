"""Guard against banned language and overstated claims (R9).

Enforces accurate terminology: forensic evidence report, hypothesis, indicator,
draft for expert review, etc.

Scans git-tracked files in target directories.
"""

import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ALLOWLIST_FILE = ROOT_DIR / "tools" / "guards" / "allowlist.txt"

BANNED_PATTERNS = [
    (re.compile(r"\bcourt[- ]ready\b", re.IGNORECASE), "court-ready / court ready"),
    (re.compile(r"\blegally admissible\b", re.IGNORECASE), "legally admissible"),
    (re.compile(r"\badmissible in court\b", re.IGNORECASE), "admissible in court"),
    (re.compile(r"\bproves\b", re.IGNORECASE), "proves"),
    (re.compile(r"\bproof of\b", re.IGNORECASE), "proof of"),
    (re.compile(r"\bguaranteed\b", re.IGNORECASE), "guaranteed"),
    (re.compile(r"\btamper[- ]proof\b", re.IGNORECASE), "tamper-proof"),
    (re.compile(r"\bdecrypts without key\b", re.IGNORECASE), "decrypts without key"),
    (re.compile(r"\bsworn\b", re.IGNORECASE), "sworn"),
    (re.compile(r"\bdemo mode\b", re.IGNORECASE), "demo mode"),
]

TARGET_DIRS = ["backend", "forensic", "frontend/src", "docs", "tools", "evaluation"]
TARGET_GLOBS = ["README*", "*.md"]


def load_allowlist() -> list[str]:
    """Load patterns from allowlist.txt."""
    if not ALLOWLIST_FILE.is_file():
        return []
    patterns = []
    for line in ALLOWLIST_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split()[0]
        patterns.append(token)
    return patterns


def is_allowlisted(rel_path: str, allowlist: list[str]) -> bool:
    """Check if relative path matches allowlist."""
    norm = rel_path.replace("\\", "/")
    for pattern in allowlist:
        if fnmatch.fnmatch(norm, pattern) or fnmatch.fnmatch(norm, pattern.rstrip("/") + "/*"):
            return True
    return False


def get_git_tracked_files() -> list[str]:
    """Retrieve git-tracked files matching target scopes."""
    try:
        output = subprocess.check_output(
            ["git", "ls-files"], cwd=str(ROOT_DIR), text=True, encoding="utf-8"
        )
        files = output.splitlines()
    except Exception:
        # Fallback if git is unavailable
        files = []
        for root, _, filenames in os.walk(str(ROOT_DIR)):
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), str(ROOT_DIR))
                files.append(rel.replace("\\", "/"))

    selected = []
    for f in files:
        f_norm = f.replace("\\", "/")
        in_target_dir = any(f_norm.startswith(td.rstrip("/") + "/") for td in TARGET_DIRS)
        in_target_glob = any(fnmatch.fnmatch(os.path.basename(f_norm), g) for g in TARGET_GLOBS)
        if in_target_dir or in_target_glob:
            selected.append(f_norm)
    return selected


def scan_file(file_path: Path) -> list[tuple[int, str, str]]:
    """Scan single file for banned language violations."""
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    for line_num, line in enumerate(content.splitlines(), start=1):
        if "<!-- guard:allow-banned-term-table -->" in line or "guard:allow-banned-language" in line:
            continue
        for regex, term_name in BANNED_PATTERNS:
            match = regex.search(line)
            if match:
                violations.append((line_num, term_name, line.strip()))
                break
    return violations


def run() -> int:
    allowlist = load_allowlist()
    files = get_git_tracked_files()
    total_violations = 0

    for rel_file in files:
        if is_allowlisted(rel_file, allowlist):
            continue
        full_path = ROOT_DIR / rel_file
        if not full_path.is_file():
            continue

        file_violations = scan_file(full_path)
        for line_num, term, snippet in file_violations:
            total_violations += 1
            print(f"{rel_file}:{line_num}: banned term '{term}' -> {snippet[:80]}")

    if total_violations > 0:
        print(f"\n[FAIL] banned_language guard found {total_violations} violation(s).")
        return 1
    print("[PASS] banned_language guard found 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
