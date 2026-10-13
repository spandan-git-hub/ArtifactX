"""Guard against forbidden cross-layer imports (R6, R15, R18, A1.3).

Architectural boundaries:
1. backend/ and forensic/ must never import:
   - tools (especially groundtruth generator R6)
   - tests
   - evaluation
   - wa_crypt_tools (GPLv3 R15)
   - telethon (dev tool only)
   - pickle (unsafe deserialization R12)

2. forensic/ must be pure (R18):
   - must never import backend
   - must never import fastapi
   - must never import sqlalchemy
"""

import ast
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

COMMON_FORBIDDEN = {
    "tools",
    "tests",
    "evaluation",
    "wa_crypt_tools",
    "telethon",
    "pickle",
}

FORENSIC_FORBIDDEN = COMMON_FORBIDDEN | {
    "backend",
    "fastapi",
    "sqlalchemy",
}


def check_module_name(mod_name: str | None, forbidden_set: set[str]) -> str | None:
    if not mod_name:
        return None
    root_mod = mod_name.split(".")[0]
    if root_mod in forbidden_set:
        return root_mod
    return None


class ImportVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, is_forensic: bool):
        self.filename = filename
        self.forbidden_set = FORENSIC_FORBIDDEN if is_forensic else COMMON_FORBIDDEN
        self.violations: list[tuple[int, str]] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            bad = check_module_name(alias.name, self.forbidden_set)
            if bad:
                self.violations.append((node.lineno, f"forbidden import '{alias.name}' ({bad})"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        bad = check_module_name(node.module, self.forbidden_set)
        if bad:
            self.violations.append((node.lineno, f"forbidden 'from {node.module} import ...' ({bad})"))
        self.generic_visit(node)


def scan_file(file_path: Path, is_forensic: bool) -> list[tuple[int, str]]:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return [(1, f"Syntax error: {e}")]

    visitor = ImportVisitor(str(file_path), is_forensic=is_forensic)
    visitor.visit(tree)
    return visitor.violations


def run() -> int:
    total_violations = 0
    targets = [
        ("backend", False),
        ("forensic", True),
    ]

    for target_dir, is_forensic in targets:
        dir_path = ROOT_DIR / target_dir
        if not dir_path.is_dir():
            continue
        for root, _, files in os.walk(str(dir_path)):
            for f in files:
                if not f.endswith(".py"):
                    continue
                full_path = Path(root) / f
                rel_path = full_path.relative_to(ROOT_DIR).as_posix()
                violations = scan_file(full_path, is_forensic=is_forensic)
                for lineno, reason in violations:
                    total_violations += 1
                    print(f"{rel_path}:{lineno}: {reason}")

    if total_violations > 0:
        print(f"\n[FAIL] forbidden_imports guard found {total_violations} violation(s).")
        return 1
    print("[PASS] forbidden_imports guard found 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
