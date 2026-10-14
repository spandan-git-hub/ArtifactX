# ArtifactX — Dependency Inventory and Licence Audit

> Maintained per `master.md` R15 and spec `01_CLEANUP.md` §A1.5.
> All licences verified directly from package distribution metadata (`importlib.metadata`).

## Production Dependencies (`requirements.txt`)

| Name | Version | Licence | Used By | Notes |
|---|---|---|---|---|
| `fastapi` | 0.142.2 | MIT | app | Web framework and REST routing |
| `uvicorn[standard]` | 0.54.0 | BSD-3-Clause | app | ASGI production server |
| `sqlalchemy` | 2.1.3 | MIT | app | Database abstraction and ORM |
| `psycopg2-binary` | 2.9.13 | LGPL with exceptions | app | PostgreSQL driver (compiled binary) |
| `psycopg[binary]` | 3.3.6 | LGPL-3.0-only | app | Modern PostgreSQL driver |
| `cryptography` | 50.0.2 | Apache-2.0 OR BSD-3-Clause | app | AES-GCM and SHA-256 primitives |
| `pydantic` | 2.13.5 | MIT | app | Data models and request/response validation |
| `pydantic-settings` | 2.15.0 | MIT | app | Settings management from environment |
| `python-multipart` | 0.0.32 | Apache-2.0 | app | Streaming multipart upload parser |
| `reportlab` | 5.0.1 | BSD (ReportLab licence) | app | In-memory PDF evidence report generation |
| `structlog` | 26.1.0 | MIT OR Apache-2.0 | app | Structured logging engine |
| `pillow` | 12.3.0 | MIT-CMU | app | Image processing and metadata inspection |
| `python-dotenv` | 1.2.4 | BSD-3-Clause | app | Environment variable loading |
| `pyyaml` | 6.0.3 | MIT | app | Acceptance criteria and config parsing |

## Development and Test Dependencies (`requirements-dev.txt`)

| Name | Version | Licence | Used By | Notes |
|---|---|---|---|---|
| `pytest` | 9.1.1 | MIT | dev | Test execution framework |
| `pytest-cov` | 7.1.0 | MIT | dev | Coverage reporting plugin |
| `httpx` | 0.28.1 | BSD-3-Clause | dev | TestClient ASGI integration testing |
| `alembic` | 1.20.0 | MIT | dev | Schema migrations engine |
| `coverage` | 7.16.2 | Apache-2.0 | dev | Coverage tracking |
| `wa-crypt-tools` | 0.2.0 (git@b16a805) | GPL-3.0-or-later | dev / tools (subprocess) | Reference tool for crypt14/crypt15 fixtures & differential testing. Never imported in `backend/` or `forensic/` (R15, DEC-007). |
| `javaobj-py3` | 0.6.1 | Apache-2.0 | dev / tools (transitive) | Java serialization reader used by `wa-crypt-tools` for crypt14 key files. |
| `pycryptodomex` | 3.24.1 | BSD-2-Clause / Public Domain | dev / tools (transitive) | Crypto library used internally by `wa-crypt-tools`. |
| `protobuf` | 7.36.2 | BSD-3-Clause | dev / tools (transitive) | Protobuf runtime used internally by `wa-crypt-tools`. |

## Licence Policy Notes

1. **Permissive Licences**: MIT, BSD, Apache-2.0, and Python Software Foundation licences are approved for unrestricted use.
2. **LGPL Dependencies**: `psycopg` and `psycopg2-binary` are dynamic runtime bindings / standard DBAPI drivers; application code does not statically modify or incorporate LGPL internals.
3. **GPL Tooling Policy (R15, DEC-007)**: Any GPL tools (such as `wa-crypt-tools` GPLv3 for B2 reference comparison) must remain dev-only, installed via `requirements-dev.txt`, executed strictly via subprocess in differential tests, and never imported in `backend/` or `forensic/`.
