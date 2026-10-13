"""Guard against demo mode and synthetic seeding remnants in application code (A2.4, R6).

Scans backend/, forensic/, frontend/src for 'demo' and 'seed' references.
Excludes tests/ and tools/groundtruth/.
"""

import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ALLOWLIST_FILE = ROOT_DIR / "tools" / "guards" / "allowlist.txt"

TARGET_DIRS = ["backend", "forensic", "frontend/src"]
DEMO_SEED_REGEX = re.compile(
    r"(?i:\b(?:demo|seed|seeding)\b)"
    r"|(?i:_demo\b|_seed\b)"
    r"|(?i:\bdemo_|\bseed_)"
    r"|(?i:_demo_|_seed_)"
    r"|\b(?:Demo|Seed)[A-Z][a-z0-9]"
    r"|\b(?:demo|seed)[A-Z][a-z0-9]"
    r"|(?<=[a-z])(?:Demo|Seed)"
)

# Allowed patterns such as technical "random seed" or explicit allow directives
ALLOWED_PATTERNS = [
    re.compile(r"guard:allow", re.IGNORECASE),
    re.compile(r"\brandom seed\b", re.IGNORECASE),
]

EXCLUDED_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".ico", ".svg", ".pyc", ".db", ".lock",
    ".woff", ".woff2", ".ttf", ".eot", ".bin"
)


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


def get_target_files() -> list[str]:
    """Retrieve tracked or present files matching target directories."""
    try:
        output = subprocess.check_output(
            ["git", "ls-files"], cwd=str(ROOT_DIR), text=True, encoding="utf-8"
        )
        files = output.splitlines()
    except Exception:
        files = []
        for target_dir in TARGET_DIRS:
            dir_path = ROOT_DIR / target_dir
            if not dir_path.is_dir():
                continue
            for root, _, filenames in os.walk(str(dir_path)):
                for f in filenames:
                    rel = os.path.relpath(os.path.join(root, f), str(ROOT_DIR))
                    files.append(rel.replace("\\", "/"))

    selected = []
    for f in files:
        f_norm = f.replace("\\", "/")
        in_target = any(f_norm.startswith(td.rstrip("/") + "/") for td in TARGET_DIRS)
        if in_target and not any(f_norm.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
            selected.append(f_norm)
    return selected


def scan_file(file_path: Path) -> list[tuple[int, str]]:
    """Scan a file for demo or seed occurrences."""
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    for line_num, line in enumerate(content.splitlines(), start=1):
        if any(p.search(line) for p in ALLOWED_PATTERNS):
            continue
        match = DEMO_SEED_REGEX.search(line)
        if match:
            violations.append((line_num, line.strip()))
    return violations


def run() -> int:
    allowlist = load_allowlist()
    target_files = get_target_files()
    total_violations = 0

    for rel_file in target_files:
        if is_allowlisted(rel_file, allowlist):
            continue
        full_path = ROOT_DIR / rel_file
        if not full_path.is_file():
            continue

        violations = scan_file(full_path)
        for lineno, snippet in violations:
            total_violations += 1
            print(f"{rel_file}:{lineno}: demo/seed found -> {snippet[:80]}")

    if total_violations > 0:
        print(f"\n[FAIL] no_demo_seed guard found {total_violations} violation(s).")
        return 1
    print("[PASS] no_demo_seed guard found 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
