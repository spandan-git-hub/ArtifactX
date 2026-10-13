"""Guard against demo mode and synthetic seeding remnants in application code (A2.4, R6).

Scans backend/, forensic/, frontend/src for 'demo' and 'seed' references.
Excludes tests/ and tools/groundtruth/.
"""

import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

TARGET_DIRS = ["backend", "forensic", "frontend/src"]
DEMO_SEED_REGEX = re.compile(r"\b(demo|seed|seeding)\b", re.IGNORECASE)

# Allowed technical terms like 'random seed' or allow comments
ALLOWED_PATTERNS = [
    re.compile(r"guard:allow", re.IGNORECASE),
]


def scan_file(file_path: Path) -> list[tuple[int, str]]:
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
    total_violations = 0
    for target_dir in TARGET_DIRS:
        dir_path = ROOT_DIR / target_dir
        if not dir_path.is_dir():
            continue
        for root, _, files in os.walk(str(dir_path)):
            if "__pycache__" in root:
                continue
            for f in files:
                full_path = Path(root) / f
                rel_path = full_path.relative_to(ROOT_DIR).as_posix()
                if any(rel_path.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".ico", ".svg", ".pyc", ".db", ".lock")):
                    continue
                violations = scan_file(full_path)
                for lineno, snippet in violations:
                    total_violations += 1
                    print(f"{rel_path}:{lineno}: demo/seed found -> {snippet[:80]}")

    if total_violations > 0:
        print(f"\n[FAIL] no_demo_seed guard found {total_violations} violation(s).")
        return 1
    print("[PASS] no_demo_seed guard found 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
