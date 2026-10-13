"""Runner for all repository guard-rails (A1.3).

Executes all guards, displays a summary table, and exits non-zero if any guard fails.
"""

import subprocess
import sys
from pathlib import Path

GUARDS_DIR = Path(__file__).resolve().parent

# Guards to execute in order
GUARDS = [
    ("banned_language", GUARDS_DIR / "banned_language.py"),
    ("no_disk_write", GUARDS_DIR / "no_disk_write.py"),
    ("forbidden_imports", GUARDS_DIR / "forbidden_imports.py"),
    ("secret_leak", GUARDS_DIR / "secret_leak.py"),
    ("no_demo_seed", GUARDS_DIR / "no_demo_seed.py"),
    ("no_assistant_sentiment", GUARDS_DIR / "no_assistant_sentiment.py"),
]


def run_guard(name: str, script_path: Path) -> tuple[bool, str, int]:
    """Execute a single guard script."""
    cmd = [sys.executable, str(script_path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        passed = (proc.returncode == 0)
        output = proc.stdout + proc.stderr
        # Count lines containing ": " that look like file:line violations
        violation_count = 0
        for line in output.splitlines():
            if ":" in line and ("found" in line or "->" in line or "call" in line or "usage" in line or "banned" in line or "forbidden" in line):
                violation_count += 1
        return passed, output, violation_count
    except Exception as e:
        return False, str(e), 1


def main() -> int:
    print("=" * 70)
    print(" ArtifactX Repository Guard-Rails (tools/guards/run_all.py)")
    print("=" * 70)

    results = []
    any_failed = False

    for name, script in GUARDS:
        if not script.is_file():
            results.append((name, "MISSING", "Script not found"))
            any_failed = True
            continue

        passed, output, vcount = run_guard(name, script)
        status = "PASS" if passed else "FAIL"
        if not passed:
            any_failed = True
        notes = f"{vcount} violation(s)" if not passed else "0 violations"
        results.append((name, status, notes, output))

    print(f"\n{'Guard Name':<28} | {'Status':<6} | {'Details':<30}")
    print("-" * 70)
    for name, status, notes, _ in results:
        print(f"{name:<28} | {status:<6} | {notes:<30}")
    print("-" * 70)

    # Print failure details
    for name, status, _, output in results:
        if status == "FAIL":
            print(f"\n--- Violations for {name} ---")
            for line in output.strip().splitlines()[:20]:
                print(f"  {line}")
            lines = output.strip().splitlines()
            if len(lines) > 20:
                print(f"  ... and {len(lines) - 20} more lines")

    if any_failed:
        print("\nResult: Guard-rails FAIL (violations detected).")
        return 1
    else:
        print("\nResult: All guard-rails PASSED.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
