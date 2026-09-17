"""
Capture Baseline Forensic Artifacts for ArtifactX Phase A.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import engine, Base
import backend.models.models  # Ensure all models are registered in Base.metadata
from backend.app.main import app
from sqlalchemy import inspect
from sqlalchemy.schema import CreateTable

SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

def capture_database_schema():
    print("[*] Capturing PostgreSQL database schema...")
    schema = {}
    ddl_statements = []

    with engine.connect() as conn:
        insp = inspect(conn)
        tables = sorted(insp.get_table_names())
        for t in tables:
            columns = insp.get_columns(t)
            fks = insp.get_foreign_keys(t)
            pk = insp.get_pk_constraint(t)
            indexes = insp.get_indexes(t)
            schema[t] = {
                "columns": [
                    {
                        "name": c["name"],
                        "type": str(c["type"]),
                        "nullable": c["nullable"],
                        "default": str(c.get("default")) if c.get("default") is not None else None,
                    }
                    for c in columns
                ],
                "primary_key": pk,
                "foreign_keys": fks,
                "indexes": indexes,
            }

    # Generate DDL using SQLAlchemy metadata
    for table_name, table in Base.metadata.tables.items():
        try:
            ddl = str(CreateTable(table).compile(engine)).strip()
            ddl_statements.append(f"{ddl};")
        except Exception as e:
            ddl_statements.append(f"-- Table {table_name}: could not generate DDL ({e})")

    schema_json_path = SNAPSHOT_DIR / "baseline_schema.json"
    with open(schema_json_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, default=str)

    schema_sql_path = SNAPSHOT_DIR / "baseline_schema.sql"
    with open(schema_sql_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(ddl_statements) + "\n")

    print(f"  -> Captured {len(schema)} tables to {schema_json_path} and {schema_sql_path}")
    return list(schema.keys())

def capture_openapi():
    print("[*] Capturing OpenAPI v3 specification...")
    openapi_schema = app.openapi()
    openapi_path = SNAPSHOT_DIR / "baseline_openapi.json"
    with open(openapi_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)

    routes = [r.path for r in app.routes if hasattr(r, "path")]
    print(f"  -> Captured OpenAPI schema with {len(routes)} routes to {openapi_path}")

def capture_git_and_system():
    print("[*] Capturing Git status and system metadata...")
    def run_cmd(args):
        try:
            res = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except Exception as e:
            return f"Error: {e}"

    git_commit = run_cmd(["git", "rev-parse", "HEAD"])
    git_branch = run_cmd(["git", "branch", "--show-current"])
    git_status = run_cmd(["git", "status", "--porcelain"])

    metadata = {
        "phase": "Phase A - Baseline Preservation",
        "git_head": git_commit,
        "git_branch": git_branch,
        "git_status": git_status,
        "python_version": sys.version,
    }

    meta_path = SNAPSHOT_DIR / "baseline_system_state.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"  -> Saved system & git metadata to {meta_path}")

def run_and_capture_phase14_test():
    print("[*] Running Phase 14 regression test and recording log...")
    import io
    from backend.scripts.test_phase14_e2e import run_phase14_smoke_test

    log_path = SNAPSHOT_DIR / "baseline_test_phase14.log"
    
    class TeeWriter(io.TextIOBase):
        def __init__(self, *writers):
            self.writers = writers
        def write(self, s):
            for w in self.writers:
                w.write(s)
                w.flush()
            return len(s)

    with open(log_path, "w", encoding="utf-8") as lf:
        orig_stdout = sys.stdout
        sys.stdout = TeeWriter(orig_stdout, lf)
        try:
            run_phase14_smoke_test()
            print(f"  -> Phase 14 regression test passed! Log saved to {log_path}")
        finally:
            sys.stdout = orig_stdout

if __name__ == "__main__":
    print("=== ARTIFACTX BASELINE PRESERVATION CAPTURE ===")
    tables = capture_database_schema()
    capture_openapi()
    capture_git_and_system()
    run_and_capture_phase14_test()
    print("=== BASELINE CAPTURE COMPLETED SUCCESSFULLY ===")
