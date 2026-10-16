"""Guard against evidence disk writes at runtime (R4, A1.3).

AST static scan of backend/ and forensic/ code for write operations:
- open(...) in write/append modes
- Path.write_text, Path.write_bytes
- shutil copy/move
- os.mkdir, os.makedirs
- tempfile.*, NamedTemporaryFile
- sqlite3.connect to non-:memory: paths

Allowlist: logging configuration only.
"""

import ast
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

ALLOWLISTED_FILES = [
    "backend/utils/logging_config.py",
]

# Function-level allowlist per DEC-011 and spec B13.3:
# CLI --out writing is the only allowed write in forensic/, confined to write_cli_output
ALLOWLISTED_FUNCTIONS = {
    ("forensic/cli.py", "write_cli_output"): "CLI output file export per DEC-011 and spec B13.3 (analysis result only, never evidence)",
}

TARGET_DIRS = ["backend", "forensic"]


class DiskWriteVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, lines: list[str], rel_path: str = ""):
        self.filename = filename
        self.lines = lines
        self.rel_path = rel_path
        self.current_func: str = ""
        self.violations: list[tuple[int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_func = self.current_func
        self.current_func = node.name
        self.generic_visit(node)
        self.current_func = prev_func

    def _is_suppressed(self, lineno: int) -> bool:
        if (self.rel_path, self.current_func) in ALLOWLISTED_FUNCTIONS:
            return True
        if 1 <= lineno <= len(self.lines):
            line = self.lines[lineno - 1]
            if "guard:allow-disk-write" in line or "guard:allow" in line:
                return True
        return False

    def visit_Call(self, node: ast.Call):
        lineno = getattr(node, "lineno", 0)
        if self._is_suppressed(lineno):
            self.generic_visit(node)
            return

        # 1. open(...) with write mode
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            mode_arg = None
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                mode_arg = node.args[1].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode_arg = kw.value.value

            if isinstance(mode_arg, str) and any(c in mode_arg for c in ("w", "a", "x", "+")):
                self.violations.append((lineno, f"open() called with write mode '{mode_arg}'"))

        # 2. Path.write_text, Path.write_bytes
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("write_text", "write_bytes"):
            self.violations.append((lineno, f"Path.{node.func.attr}() write call"))

        # 3. shutil copy/move/rmtree
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "shutil" and node.func.attr in (
                "copy", "copy2", "copyfile", "copymode", "copystat", "copytree", "move", "rmtree"
            ):
                self.violations.append((lineno, f"shutil.{node.func.attr}() file operation"))

        # 4. os.mkdir, os.makedirs
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "os" and node.func.attr in ("mkdir", "makedirs"):
                self.violations.append((lineno, f"os.{node.func.attr}() directory creation"))

        # 5. tempfile.*
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "tempfile":
                self.violations.append((lineno, f"tempfile.{node.func.attr}() usage"))
        if isinstance(node.func, ast.Name) and node.func.id in ("NamedTemporaryFile", "TemporaryFile", "mkdtemp"):
            self.violations.append((lineno, f"{node.func.id}() usage"))

        # 6. sqlite3.connect to non-:memory: path
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "sqlite3" and node.func.attr == "connect":
                if node.args and isinstance(node.args[0], ast.Constant):
                    db_path = str(node.args[0].value)
                    if db_path != ":memory:":
                        self.violations.append((lineno, f"sqlite3.connect to disk file '{db_path}'"))

        self.generic_visit(node)


def scan_file(file_path: Path) -> list[tuple[int, str]]:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return [(1, f"Syntax / Parse error: {e}")]

    try:
        rel_path = file_path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        rel_path = str(file_path).replace("\\", "/")

    visitor = DiskWriteVisitor(str(file_path), content.splitlines(), rel_path=rel_path)
    visitor.visit(tree)
    return visitor.violations


def run() -> int:
    total_violations = 0
    for target_dir in TARGET_DIRS:
        dir_path = ROOT_DIR / target_dir
        if not dir_path.is_dir():
            continue
        for root, _, files in os.walk(str(dir_path)):
            for f in files:
                if not f.endswith(".py"):
                    continue
                full_path = Path(root) / f
                rel_path = full_path.relative_to(ROOT_DIR).as_posix()
                if any(rel_path == allow or rel_path.endswith(allow) for allow in ALLOWLISTED_FILES):
                    continue

                violations = scan_file(full_path)
                for lineno, reason in violations:
                    total_violations += 1
                    print(f"{rel_path}:{lineno}: {reason}")

    if total_violations > 0:
        print(f"\n[FAIL] no_disk_write guard found {total_violations} violation(s).")
        return 1
    print("[PASS] no_disk_write guard found 0 violations.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
