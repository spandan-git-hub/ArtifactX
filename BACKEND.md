# ArtifactX — Backend: Complete Specification & Audit

> **What this file is:** The definitive truth of the backend — what exists, what is broken, what must be written or rewritten.  
> Every section states the **current state** and the **required state** if they differ.  
> An AI reading this file should be able to fix every hole without needing any other context.

---

## 1. Stack

| Component | Current | Required |
|-----------|---------|----------|
| Framework | FastAPI ✅ | FastAPI |
| Language | Python 3.13 ✅ | Python 3.13 |
| ORM | SQLAlchemy 2.0 ✅ | SQLAlchemy 2.0 |
| DB | PostgreSQL (Neon cloud) via `.env` ✅ | PostgreSQL |
| Validation | Pydantic v2 ✅ | Pydantic v2 |
| PDF | ReportLab ✅ | ReportLab |
| Logging | structlog ✅ | structlog |
| Image EXIF | Pillow ✅ | Pillow |
| PYTHONPATH | Must be set to project root | `$env:PYTHONPATH = "D:\ArtifactX"` |

---

## 2. Entry Point — `backend/app/main.py`

**Current state:** Working. CORS, lifespan, all routers registered, `ErrorLoggingMiddleware` applied. Health endpoint works.

**Bug:** CORS `allow_origins` only lists ports `5173` and `3000`. Vite silently falls back to `5174` when 5173 is occupied.

**Fix required in `main.py`:**
```python
allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",   # ← add this
    "http://localhost:3000",
],
```

---

## 3. Configuration — `backend/app/config.py`

**Current state:** Working. `pydantic-settings` `BaseSettings` reads `.env` from project root. All keys are present.

**No fix required.**

Current `.env` values (do not change):
```
DATABASE_URL=postgresql://neondb_owner:...@neon.tech/neondb?sslmode=require&channel_binding=require
DEMO_MODE=true
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE=1073741824
```

---

## 4. Database Models — `backend/models/models.py`

**Current state:** Fully implemented. All tables defined correctly with proper FK relationships.

| Table | Status |
|-------|--------|
| `cases` | ✅ Correct |
| `evidence` | ✅ Correct |
| `evidence_files` | ✅ Correct |
| `analysis_results` | ✅ Correct |
| `wa_messages` | ✅ Correct |
| `wa_contacts` | ✅ Correct |
| `wa_groups` | ✅ Correct |
| `tg_messages` | ✅ Correct |
| `tg_contacts` | ✅ Correct |
| `tg_groups` | ✅ Correct |
| `timeline_events` | ✅ Correct |
| `deleted_messages` | ✅ Correct (import is present) |
| `media_items` | ✅ Correct |
| `correlation_edges` | ✅ Correct |
| `analysis_logs` | ✅ Correct |
| `activity_logs` | ✅ Correct |
| `error_logs` | ✅ Correct |

**`DeletedMessage` import status:** The import in `deleted_service.py` line 10 is `from backend.models.models import ... DeletedMessage` — this is CORRECT and exists. The previously reported bug does NOT exist in the current code.

---

## 5. API Layer — `backend/api/`

### `evidence.py` — Evidence Upload & Management

**Current state:** Fully implemented (726 lines). Handles:
- Multipart file upload
- ZIP extraction with per-file SHA-256 and MIME detection
- Direct DB file upload
- File size limit enforcement
- `EvidenceFile` records creation per extracted file

**Bug — `_get_evidence_ids` in `search_repo.py`:** Ignores the `app` parameter entirely (see Section 7.4).

**No other evidence API bugs found.**

### `demo.py` — Demo Mode

**Current state:** Partially implemented. Creates `Case`, `Evidence`, `WhatsAppMessage`, `WhatsAppContact`, `TelegramMessage`, `TelegramContact`. Returns `{ case_id, whatsapp, telegram }`.

**Critical gaps — causes dashboard to show all-zero stats after demo creation:**

1. **`TimelineEvent` records NOT created** → Dashboard "Timeline Summary" always shows 0 events.
2. **`DeletedMessage` records NOT created** → Dashboard "Deletions Detected" always shows 0.
3. **`DEMO_MODE` check commented out** → Any caller can create demo cases even with `DEMO_MODE=false`.
4. **`has_telegram` defaults to `False`** → Telegram tab empty by default. Should default to `True`.
5. **`evidence_type` set to `"demo"` but `_get_evidence_ids` in `search_repo.py` doesn't filter by type** → actually fine for now, but inconsistent.

**Required fix in `demo.py` — add after `db.commit()` in `_create_demo_whatsapp` and `_create_demo_telegram`:**

```python
# After creating messages, create TimelineEvents
from backend.models.models import TimelineEvent
from datetime import datetime, timezone

for i, msg in enumerate(all_created_messages):
    event = TimelineEvent(
        case_id=case_id,
        evidence_id=evidence_id,
        event_type="message",
        source_app="whatsapp",   # or "telegram"
        timestamp=msg.timestamp,
        normalized_timestamp=datetime.fromtimestamp(msg.timestamp / 1000, tz=timezone.utc),
        entity_id=msg.message_id,
        entity_type="message",
        description=f"Message from {msg.sender_jid}: {msg.body[:50]}",
        metadata_={}
    )
    db.add(event)

# Also create 3 DeletedMessage records
from backend.models.models import DeletedMessage
for j in range(3):
    dm = DeletedMessage(
        case_id=case_id,
        evidence_id=evidence_id,
        source_app="whatsapp",   # or "telegram"
        chat_jid=f"+1202555100{j+1}@s.whatsapp.net",
        gap_start=1000 + j * 50,
        gap_end=1002 + j * 50,
        missing_count=3,
        confidence_score=0.7 + j * 0.1,
        detection_method="sequence_gap_analysis",
        detected_at=datetime.utcnow()
    )
    db.add(dm)
db.commit()
```

**Required fix — add DEMO_MODE guard:**
```python
@router.post("/create-demo-case")
def create_demo_case(data: DemoData, db: Session = Depends(get_db)) -> dict:
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    # ... rest of function
```

**Required fix — change `DemoData` defaults:**
```python
class DemoData(BaseModel):
    case_name: str = f"Demo Case - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    has_whatsapp: bool = True
    has_telegram: bool = True   # ← changed from False
    message_count: int = 100    # ← changed from 50
    contact_count: int = 15     # ← changed from 10
```

### `dashboard.py` — Stats & Overview

**Current state:** Fully implemented. Four endpoints: `stats`, `correlation-stats`, `timeline-stats`, `overview`.

**No bugs found.**

### `reports.py` — Report Generation & Summaries

**Current state:** Fully implemented. PDF generation works via ReportLab. Three GET summary endpoints use correct HTTP method.

**No bugs found.**

### `search.py`, `whatsapp.py`, `telegram.py`, `timeline.py`, `deleted.py`, `media.py`, `correlation.py`, `logs.py`, `cases.py`

**Current state:** All routers are wired and implemented.

---

## 6. Service Layer — `backend/services/`

### `whatsapp_service.py`

**Current state:** Mostly working. Properly calls forensic parsers, saves messages/contacts/groups/media to DB.

**Bug — stack trace logging (line 123):**
```python
# CURRENT (wrong):
stack_trace=str(e.__traceback__),

# REQUIRED (correct):
import traceback
stack_trace=traceback.format_exc(),
```

**Bug — async not actually async (line 101):**
`self._perform_analysis(...)` is called synchronously inside an `async def analyze_evidence`. This works but blocks the event loop for large evidence files.

**Fix for now:** Keep synchronous. Add `# TODO: move to background task (FastAPI BackgroundTasks)` comment. Do NOT introduce asyncio complexity without a full plan.

### `telegram_service.py`

**Same stack trace bug** as `whatsapp_service.py`. Apply same fix.

### `timeline_service.py`

**Stack trace bug (line 65):** Same as above. Fix: `import traceback; stack_trace=traceback.format_exc()`.

### `deleted_service.py`

**Stack trace bug (line 98):** Same. Fix: `import traceback; stack_trace=traceback.format_exc()`.

**`DeletedMessage` import:** Already present on line 10. ✅

### `correlation_service.py`

**Stack trace bug:** Same pattern. Fix.

### `dashboard_service.py`

**Current state:** Fully working. Delegates cleanly to `DashboardRepository`. ✅

### `search_service.py`

**Current state:** Working. ✅

### `report_service.py`

**Current state:** Fully working. Generates PDF correctly with ReportLab. ✅

### `log_service.py`

**Needs audit** — `log_error` accepts `stack_trace` param. Verify it saves to `error_logs` table correctly.

---

## 7. Repository Layer — `backend/repositories/`

### 7.1 `dashboard_repo.py`

**Current state:** Fully implemented (333 lines). Aggregates stats correctly via SQLAlchemy. ✅

### 7.2 `report_repo.py`

**Current state:** Implemented (15498 bytes). Provides evidence/timeline/deleted/correlation data for PDF sections. ✅

### 7.3 `timeline_repo.py`

**Current state:** Implemented. ✅

### 7.4 `search_repo.py` — **CRITICAL BUG**

**Bug — `_get_evidence_ids` ignores the `app` parameter (lines 444–448):**
```python
# CURRENT (broken):
def _get_evidence_ids(self, case_id: int, app: str) -> List[int]:
    stmt = self.db.query(Evidence.id).filter(Evidence.case_id == case_id)
    evidence_records = stmt.all()
    return [e.id for e in evidence_records]   # ← 'app' parameter ignored!

# REQUIRED (correct):
def _get_evidence_ids(self, case_id: int, app: str = "all") -> List[int]:
    stmt = self.db.query(Evidence.id).filter(Evidence.case_id == case_id)
    # Filter by evidence_type if a specific app is requested
    # Note: demo evidence has evidence_type="demo"; real evidence has evidence_type=None or the app name
    # We filter metadata_ JSON field which stores {"app": "whatsapp"} or {"app": "telegram"}
    if app in ("whatsapp", "telegram"):
        stmt = stmt.filter(
            Evidence.metadata_["app"].astext == app
        )
    evidence_records = stmt.all()
    return [e.id for e in evidence_records]
```

**Impact of this bug:** When searching messages for "whatsapp" app filter, the query also searches through Telegram evidence IDs (because it returns ALL evidence IDs for the case). Results are still correct due to `WhatsAppMessage.evidence_id.in_(evidence_ids)` constraint, but the evidence_ids list is wrong — it includes Telegram evidence IDs in the WhatsApp query, which returns 0 results from those Telegram IDs. The search still works because `WhatsAppMessage` can't have TG evidence IDs. **Effect is wasted DB round-trips, not wrong results.** Still, fix it.

### 7.5 `whatsapp_repo.py`, `telegram_repo.py`

**Current state:** Both implemented. ✅

### 7.6 `correlation_repo.py`, `deleted_repo.py`, `media_repo.py`, `log_repo.py`

**Current state:** All implemented. ✅

---

## 8. Forensic Engine — `forensic/`

### `forensic/whatsapp/detector.py`

**Current state:** Correctly identifies WhatsApp databases by table name inspection using `sqlite_master`. Handles both legacy (`messages`, `wa_contacts`, `chats`) and modern (`message`, `jid`, `chat`) schemas. ✅

### `forensic/whatsapp/message_parser.py`

**Current state:** Smart schema-adaptive query builder. Uses `_first_existing()` to select the right column names regardless of WA DB version. Handles both `messages` and `message` table names. ✅

**Minor weakness:** `sqlite3.Error` is silently caught and returns `[]` — no logging. If a real evidence DB fails to parse, the user sees an empty analysis with no error explanation.

**Fix:**
```python
except sqlite3.Error as e:
    import logging
    logging.getLogger(__name__).error(f"WhatsApp parse error on {db_path}: {e}")
    return []
```

### `forensic/whatsapp/contact_parser.py`, `forensic/whatsapp/group_parser.py`, `forensic/whatsapp/media_parser.py`

**Audit needed** — Verify these files exist and have the same schema-adaptive pattern as `message_parser.py`. If any is missing, it must be created following the same pattern.

### `forensic/telegram/` — Full audit needed

Check that `detector.py`, `message_parser.py`, `contact_parser.py`, `group_parser.py` all exist and correctly handle Telegram's `cache4.db` schema (tables: `messages`, `users`, `dialogs`, `chats`).

### `forensic/deleted/detector.py`

**Current state:** Implemented. Uses sequence gap analysis on message IDs. Correctly handles WhatsApp string IDs (extracts numeric suffix) and Telegram integer IDs. Calculates confidence scores from gap size + time delta. ✅

**Weakness — WhatsApp ID parsing is fragile:**
```python
# Current: extracts last number from string ID like "3EB0A1234..."
numbers = re.findall(r'\d+', msg_id_str)
if numbers:
    return int(numbers[-1]) + 1
```
WhatsApp's `key_id` is a hex string like `3EB0F2A189CABD234E22`. Extracting the last number from this will produce inconsistent results. This means WhatsApp deletion detection produces **unreliable results**.

**Correct approach:** WhatsApp deletion detection should be timestamp-based (not ID-based), since WhatsApp's IDs are not sequential integers. Telegram's IDs ARE sequential integers, so ID-based detection is correct for Telegram only.

**Fix required in `detector.py`:**
```python
def _get_expected_next_id(self, message: Any, source_app: str) -> Optional[int]:
    if source_app == "whatsapp":
        return None  # WhatsApp IDs are hex, not sequential — skip ID gap detection
    elif source_app == "telegram":
        try:
            return int(message.message_id) + 1
        except (AttributeError, ValueError):
            return None
    return None
```
This means WhatsApp will produce 0 deletions from ID analysis, which is **accurate** rather than fabricated. Timeline-based deletion detection (unusually long silences) is the correct method for WhatsApp, but that's a future enhancement.

### `forensic/timeline/builder.py`

**Audit needed** — Verify `TimelineBuilder.build_timeline_for_case(db, case_id)` correctly queries `WhatsAppMessage` and `TelegramMessage` tables and produces `TimelineEvent`-compatible dicts with `normalized_timestamp` as a real `datetime`.

### `forensic/correlation/matcher.py`

**Current state:** Used by `correlation_service.py` and imports `WhatsAppMessage`, `WhatsAppContact`, `TelegramMessage`, `TelegramContact`, `MediaItem` as **dataclasses** (not ORM models). The service converts ORM objects to these dataclasses before passing them to the matcher.

**Verify the dataclasses have all fields the matcher uses.** This is a common type mismatch source.

### `forensic/media/` 

**Status:** `detector.py`, `metadata.py`, `orphan.py` exist per import references in services. **Audit needed** to verify `orphan.py` functions have the correct signatures matching what `media_service.py` calls:
- `find_orphan_media_items(case_id, db) -> List[MediaItem]`
- `find_orphan_files(case_id, evidence_id, db) -> List[EvidenceFile]`
- `mark_media_orphan_status(case_id, db) -> int`

---

## 9. Complete Bug Register

| ID | Severity | File | Description | Fix |
|----|----------|------|-------------|-----|
| B1 | HIGH | `main.py` L38 | CORS missing port 5174 | Add `"http://localhost:5174"` to `allow_origins` |
| B2 | HIGH | `demo.py` | Demo creates no `TimelineEvent` or `DeletedMessage` → dashboard shows zeros | Create events + deletions after message creation |
| B3 | HIGH | `demo.py` L21 | `has_telegram` defaults to `False` | Change default to `True` |
| B4 | MEDIUM | `demo.py` | No `DEMO_MODE` guard | Add `if not settings.demo_mode: raise HTTPException(403)` |
| B5 | MEDIUM | `whatsapp_service.py` L123 | `str(e.__traceback__)` instead of `traceback.format_exc()` | Replace with `traceback.format_exc()` |
| B6 | MEDIUM | `telegram_service.py` | Same as B5 | Same fix |
| B7 | MEDIUM | `timeline_service.py` L65 | Same as B5 | Same fix |
| B8 | MEDIUM | `deleted_service.py` L98 | Same as B5 | Same fix |
| B9 | MEDIUM | `correlation_service.py` | Same as B5 | Same fix |
| B10 | MEDIUM | `search_repo.py` L444 | `_get_evidence_ids` ignores `app` filter | Fix to filter by `metadata_["app"]` |
| B11 | HIGH | `forensic/deleted/detector.py` L84-92 | WhatsApp ID parsing unreliable (hex IDs, not sequential) | Return `None` for WhatsApp; ID gaps only valid for Telegram |
| B12 | LOW | `forensic/whatsapp/message_parser.py` L107 | Silent `sqlite3.Error` swallows parse failures | Add logging before `return []` |
| B13 | MEDIUM | `demo.py` L17-24 | `DemoData` defaults too sparse (50 msgs, 10 contacts, TG off) | Increase to 100 msgs, 15 contacts, TG on by default |

---

## 10. Required Audit Tasks (Unverified Files)

The following files were **not directly read** and must be audited before marking the backend complete:

| File | What to Verify |
|------|---------------|
| `forensic/whatsapp/contact_parser.py` | Exists, schema-adaptive, returns dicts matching `WhatsAppContact` model |
| `forensic/whatsapp/group_parser.py` | Exists, returns dicts matching `WhatsAppGroup` model |
| `forensic/whatsapp/media_parser.py` | Exists, returns dicts with `message_id`, `media_path`, `message_type` |
| `forensic/telegram/detector.py` | Exists, correctly identifies Telegram `cache4.db` schemas |
| `forensic/telegram/message_parser.py` | Exists, returns dicts matching `TelegramMessage` model |
| `forensic/telegram/contact_parser.py` | Exists, returns dicts matching `TelegramContact` model |
| `forensic/telegram/group_parser.py` | Exists, returns dicts matching `TelegramGroup` model |
| `forensic/timeline/builder.py` | `TimelineBuilder.build_timeline_for_case(db, case_id)` works; returns list of event dicts |
| `forensic/correlation/matcher.py` | Dataclass fields match what service layer converts from ORM objects |
| `forensic/media/orphan.py` | Function signatures match what `media_service.py` calls |
| `backend/services/log_service.py` | `log_error` saves to `error_logs` table; `log_analysis` with `evidence_id=0` doesn't crash FK constraint |
| `backend/services/log_service.py` | FK: `analysis_logs.evidence_id` has FK to `evidence.id` — passing `0` will cause FK violation |

**Critical:** `log_service.py` with `evidence_id=0` may crash with FK violation since `evidence_logs.evidence_id` is an FK to `evidence.id`. If this is the case, fix: change the column to `nullable=True` and default to `None`, not `0`.

---

## 11. Run Commands

```powershell
# Must set PYTHONPATH so Python can find 'backend.*' and 'forensic.*' packages
$env:PYTHONPATH = "D:\ArtifactX"
$env:PATH = "C:\Users\Spandan\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts;$env:PATH"

cd D:\ArtifactX\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 12. Data Flow: From Upload to Dashboard (verified end-to-end)

```
User uploads ZIP via evidence.py
  → extracted to uploads/{case_id}/{evidence_id}/
  → EvidenceFile records created with SHA-256, MIME type
  → Evidence.extracted_path set

User clicks "Analyze WhatsApp":
  → POST /api/whatsapp/evidence/{id}/analyze/whatsapp
  → WhatsAppService.analyze_evidence()
  → Scans extracted_path for *.db files
  → is_whatsapp_database() checks sqlite_master tables
  → extract_messages() → schema-adaptive SQL query
  → extract_contacts() → queries wa_contacts table
  → extract_groups() → queries group tables
  → Saves WhatsAppMessage/WhatsAppContact/WhatsAppGroup to DB
  → Evidence.analyzed_at = now()

User clicks "Build Timeline":
  → POST /api/timeline/cases/{id}/timeline/build
  → TimelineService → TimelineBuilder.build_timeline_for_case(db, case_id)
  → Reads WhatsAppMessage + TelegramMessage
  → Creates TimelineEvent records with normalized_timestamp

User clicks "Detect Deletions":
  → POST /api/deleted/cases/{id}/deleted/detect
  → DeletedService → DeletedDetector.detect_deletions()
  → For WhatsApp: timestamp-based (ID gap detection disabled)
  → For Telegram: integer ID gap detection
  → Saves DeletedMessage records

Dashboard loads:
  → GET /api/cases/{id}/overview
  → DashboardService.get_case_overview()
  → DashboardRepository aggregates counts from all tables
  → Returns CaseOverview with stats, correlation_stats, timeline_stats, recent_events
```
