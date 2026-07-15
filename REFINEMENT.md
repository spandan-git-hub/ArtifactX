# ArtifactX Refinement Guidelines

> Last updated: 2026-07-15

## Overview

This document contains guidelines to fix existing issues and enhance ArtifactX with a demo mode for testing without real evidence files.

---

## Part 1: Error Fixes

### 1.1 Critical Backend Errors

#### Issue 1: Missing DeletedMessage Import
**File:** `backend/services/deleted_service.py`
**Problem:** The `DeletedMessage` model is used on line 45 but not imported.

**Fix:**
```python
# Add to imports section
from backend.models.models import WhatsAppMessage, TelegramMessage, Evidence, DeletedMessage
```

#### Issue 2: Empty Forensic Module Init
**File:** `forensic/__init__.py`
**Problem:** The file is completely empty, which can cause import issues.

**Fix:**
```python
"""Forensic analysis engine for ArtifactX."""

from forensic.whatsapp.detector import WhatsAppDetector
from forensic.telegram.detector import TelegramDetector
from forensic.timeline.builder import TimelineBuilder
from forensic.deleted.detector import DeletedDetector
from forensic.media.detector import detect_media_type
from forensic.correlation.matcher import correlate_all

__all__ = [
    "WhatsAppDetector",
    "TelegramDetector", 
    "TimelineBuilder",
    "DeletedDetector",
    "detect_media_type",
    "correlate_all",
]
```

#### Issue 3: Error Traceback Handling
**File:** Multiple `*_service.py` and `*_api.py` files
**Problem:** Using `str(e.__traceback__)` doesn't give useful stack traces.

**Fix - Use `traceback.format_exc()` instead:**
```python
import traceback

# Replace:
stack_trace=str(e.__traceback__)

# With:
stack_trace=traceback.format_exc()
```

Files affected: `backend/services/log_service.py` (logging functions), all service files

### 1.2 API Endpoint Corrections

#### Issue 4: Inconsistent Evidence Endpoints
**File:** `backend/api/evidence.py`
**Problem:** The evidence upload endpoint is at `/upload` but requires `case_id` as a query parameter instead of path parameter. This is inconsistent with REST conventions.

**Recommendation:** Update frontend service (`evidenceService.js`) to properly pass `case_id` as a query parameter, or create a nested endpoint `/cases/{case_id}/evidence`.

#### Issue 5: WhatsApp/Telegram Analysis Endpoints
**Location:** `backend/api/whatsapp.py`, `backend/api/telegram.py`
**Problem:** Endpoints use `/whatsapp` and `/telegram` prefixes but are included in `main.py` with different paths.

**Current in main.py:**
```python
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["whatsapp"])
```

**Fix ensure consistency - Check that frontend service calls match these paths:**
- `/api/whatsapp/evidence/{evidence_id}/analyze/whatsapp`
- `/api/whatsapp/evidence/{evidence_id}/wa-messages`
- `/api/telegram/evidence/{evidence_id}/tg-messages`

### 1.3 Frontend Error Handling Improvements

#### Issue 6: Dashboard Null Checks
**File:** `frontend/src/pages/DashboardPage.jsx`
**Problem:** Code accesses `stats.whatsapp` and `stats.telegram` without proper null checks.

**Fix:**
```javascript
{apps?.includes('whatsapp') && stats?.whatsapp && (
  <AppStatsCard app="WhatsApp" stats={stats.whatsapp} icon="whatsapp" />
)}
{apps?.includes('telegram') && stats?.telegram && (
  <AppStatsCard app="Telegram" stats={stats.telegram} icon="telegram" />
)}
```

#### Issue 7: Date Formatting Safety
**File:** `frontend/src/pages/CaseListPage.jsx`
**Problem:** `new Date(caseItem.created_at).toLocaleDateString()` may throw if `created_at` is null.

**Fix:**
```javascript
{caseItem.created_at && new Date(caseItem.created_at).toLocaleDateString()}
```

#### Issue 8: Unused Navigation Items
**File:** `frontend/src/components/layout/index.jsx`
**Problem:** Search, Reports, and Logs navigation items are disabled with `disabled: true` but still render.

**Fix:** Remove disabled items or add a tooltip explaining they're case-specific features.

### 1.4 Missing Components

#### Issue 9: Media Orphan Detection Returns
**File:** `forensic/media/orphan.py`
**Problem:** Ensure all functions return proper types as documented.

**Verify imports and return types:**
```python
def find_orphan_media_items(case_id: int, db: Session) -> List[MediaItem]:
    """Returns list of MediaItem records not linked to messages."""
    ...

def find_orphan_files(case_id: int, evidence_id: int, db: Session) -> List[EvidenceFile]:
    """Returns list of EvidenceFile records marked as media."""
    ...

def mark_media_orphan_status(case_id: int, db: Session) -> int:
    """Returns count of items marked as orphan."""
    ...
```

### 1.5 Database Schema Issues

#### Issue 10: metadata_ Column Name
**File:** `backend/models/models.py`
**Problem:** Using `"metadata_"` as the column name with `metadata_ = Column("metadata_", JSON, default=dict)` is redundant but acceptable. Ensure all usages match.

---

## Part 2: Demo Mode Implementation

### 2.1 Overview

Add a demo mode that allows users to explore ArtifactX functionality with realistic mock data without uploading actual evidence files.

### 2.2 Backend Demo Mode

#### 2.2.1 Demo Mode API

**New file:** `backend/api/demo.py`

```python
"""Demo mode endpoints for testing without real evidence."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.database import get_db
from backend.models.models import Case, Evidence, WhatsAppMessage, WhatsAppContact, TelegramMessage

router = APIRouter()


class DemoData(BaseModel):
    """Demo data structure."""
    case_name: str
    has_whatsapp: bool = True
    has_telegram: bool = True
    message_count: int = 50
    contact_count: int = 20


@router.post("/create-demo-case")
def create_demo_case(data: DemoData, db: Session = Depends(get_db)) -> int:
    """
    Create a demo case with mock forensic data.
    Returns the case ID.
    """
    import random
    from datetime import datetime, timedelta
    
    # Create case
    case = Case(
        name=data.case_name,
        description="Demo case created for testing purposes",
        status="active"
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    # Create demo evidence
    evidence = Evidence(
        case_id=case.id,
        original_filename="demo_whatsapp.db",
        storage_path="demo",
        sha256="0" * 64,  # Dummy hash
        evidence_type="demo",
        metadata_={"source": "demo"}
    )
    db.add(evidence)
    
    # Create demo WhatsApp data if requested
    if data.has_whatsapp:
        _create_demo_whatsapp(db, evidence.id, data.message_count, data.contact_count)
    
    db.commit()
    return case.id


def _create_demo_whatsapp(db, evidence_id, message_count, contact_count):
    """Create demo WhatsApp messages and contacts."""
    import random
    from datetime import datetime, timedelta
    
    # Demo contacts
    contacts_data = [
        ("+12025551234", "Alice Johnson"),
        ("+12025551235", "Bob Smith"),
        ("+12025551236", "Carol Williams"),
        ("+12025551237", "David Brown"),
        ("+12025551238", "Eve Davis"),
    ]
    
    for phone, name in contacts_data[:min(contact_count, len(contacts_data))]:
        contact = WhatsAppContact(
            evidence_id=evidence_id,
            jid=f"{phone}@s.whatsapp.net",
            display_name=name,
            phone_number=phone
        )
        db.add(contact)
    
    # Demo messages
    base_time = datetime.utcnow() - timedelta(days=7)
    sample_messages = [
        "Hey, how are you?",
        "Can you send me the documents?",
        "Meeting at 3pm today",
        "Did you see the news?",
        "Thanks for your help!",
        "Let's grab lunch tomorrow",
        "The report is ready",
        "Can you call me back?",
        "Happy birthday!",
        "See you later!",
    ]
    
    for i in range(min(message_count, 100)):
        sender_idx = i % 5
        sender = f"+12025551{234 + sender_idx}@s.whatsapp.net"
        msg = WhatsAppMessage(
            evidence_id=evidence_id,
            message_id=f"demo_msg_{i}",
            key_remote_jid="+12025551000@g.us",  # Group chat
            sender_jid=sender,
            body=sample_messages[i % len(sample_messages)],
            timestamp=int((base_time + timedelta(minutes=i * 5)).timestamp() * 1000),
            message_type="text"
        )
        db.add(msg)
    
    # Create demo media reference
    media_msg = WhatsAppMessage(
        evidence_id=evidence_id,
        message_id="demo_media_msg",
        key_remote_jid="+12025551000@s.whatsapp.net",
        sender_jid="+12025551234@s.whatsapp.net",
        body="Check out this photo!",
        timestamp=int((base_time + timedelta(hours=3)).timestamp() * 1000),
        media_type="image",
        media_path="/demo/photos/image01.jpg"
    )
    db.add(media_msg)
```

#### 2.2.2 Update Main Router

**File:** `backend/app/main.py`

Add after existing routers:
```python
from backend.api.demo import router as demo_router
# ...
app.include_router(demo_router, prefix="/api/demo", tags=["demo"])
```

### 2.3 Frontend Demo Mode

#### 2.3.1 Demo Service

**New file:** `frontend/src/services/demoService.js`

```javascript
import axios from 'axios';

const API_BASE = '/api';

export const demoService = {
  createDemoCase: async (options = {}) => {
    const defaults = {
      case_name: 'Demo Case - ' + new Date().toLocaleDateString(),
      has_whatsapp: true,
      has_telegram: false,
      message_count: 50,
      contact_count: 20,
    };
    const config = { ...defaults, ...options };
    const response = await axios.post(`${API_BASE}/demo/create-demo-case`, config);
    return response.data;
  },
};
```

#### 2.3.2 Demo Mode Button on Home Page

**File:** `frontend/src/App.jsx` (HomeScreen component)

Add a demo button:
```javascript
const handleCreateDemo = async () => {
  try {
    const caseId = await demoService.createDemoCase();
    window.location.href = `/cases/${caseId}`;
  } catch (err) {
    alert('Failed to create demo case');
  }
};

// In JSX, add button after "Access Dashboard"
<button 
  onClick={handleCreateDemo}
  className="btn-secondary inline-flex items-center gap-2"
>
  Create Demo Case
</button>
```

#### 2.3.3 Update Home Screen

**File:** `frontend/src/App.jsx`

Add demo service import:
```javascript
import { demoService } from './services/demoService';
```

### 2.4 Demo Mode Toggle

Add an environment variable to control demo mode:

**File:** `backend/app/config.py`

```python
demo_mode: bool = False  # Enable demo mode with mock data
```

**File:** `backend/api/demo.py`

Add check:
```python
@router.post("/create-demo-case")
def create_demo_case(data: DemoData, db: Session = Depends(get_db)) -> int:
    if not settings.demo_mode:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    # ... rest of implementation
```

---

## Part 3: Additional Improvements

### 3.1 API Health Check Enhancement

**File:** `backend/app/main.py`

```python
@app.get("/api/health")
def health_check():
    return {
        "status": "ok", 
        "app": settings.app_name,
        "version": "1.0.0",
        "demo_mode": settings.demo_mode
    }
```

### 3.2 Frontend Health Check

**File:** `frontend/src/services/healthService.js`

```javascript
import axios from 'axios';

const API_BASE = '/api';

export const healthService = {
  check: async () => {
    const response = await axios.get(`${API_BASE}/health`);
    return response.data;
  },
  
  isDemoMode: async () => {
    const health = await healthService.check();
    return health.demo_mode || false;
  },
};
```

### 3.3 Better Error Boundaries

**File:** `frontend/src/components/common/ErrorBoundary.jsx`

```javascript
import { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
```

### 3.4 Loading State Component

**File:** `frontend/src/components/common/LoadingSpinner.jsx`

```javascript
import { Loader2 } from 'lucide-react';

const LoadingSpinner = ({ message = 'Loading...' }) => (
  <div className="flex items-center justify-center py-12">
    <Loader2 className="h-8 w-8 animate-spin text-accent-cyan" />
    <span className="ml-3 text-forensic-400">{message}</span>
  </div>
);

export default LoadingSpinner;
```

### 3.5 Empty State Component

**File:** `frontend/src/components/common/EmptyState.jsx`

```javascript
import { FolderOpen } from 'lucide-react';

const EmptyState = ({ 
  icon: Icon = FolderOpen, 
  title, 
  description, 
  action 
}) => (
  <div className="card text-center py-16">
    <div className="w-16 h-16 rounded-2xl bg-forensic-800 flex items-center justify-center mx-auto mb-4">
      <Icon className="h-8 w-8 text-forensic-500" />
    </div>
    <h3 className="text-lg font-semibold mb-2">{title}</h3>
    <p className="text-forensic-500 mb-6 max-w-sm mx-auto">{description}</p>
    {action}
  </div>
);

export default EmptyState;
```

---

## Part 4: Verification Checklist

After making all changes, verify:

### Backend
- [ ] Backend starts without errors: `cd backend && uvicorn app.main:app --reload`
- [ ] Health endpoint responds: `GET /api/health`
- [ ] Cases CRUD works
- [ ] Demo mode creates case with mock data
- [ ] No Python import errors

### Frontend
- [ ] Frontend builds without errors: `cd frontend && npm run build`
- [ ] Development server starts: `cd frontend && npm run dev`
- [ ] No JavaScript console errors at runtime
- [ ] Demo case creation works
- [ ] Dashboard displays mock data correctly

### Integration
- [ ] Full workflow: Create case → Upload evidence → View dashboard
- [ ] Demo mode workflow: Create demo case → View data → Generate report

---

## Part 5: PostgreSQL Database

### 5.1 Overview

ArtifactX uses PostgreSQL as the application database. PostgreSQL provides better concurrency, scalability, and advanced features required for forensic analysis workflows.

**Note:** The forensic module still uses Python's built-in `sqlite3` module to **read evidence files** (WhatsApp/Telegram databases extracted from phones), but this is separate from the application database.

### 5.2 Prerequisites

- PostgreSQL 14+ installed
- Access to create databases and users
- `psycopg2-binary` package for Python

### 5.3 Dependencies Update

**File:** `backend/requirements.txt`

PostgreSQL dependency included:
```
# Database
psycopg2-binary==2.9.9  # PostgreSQL adapter
alembic==1.13.1          # Database migrations (optional but recommended)
```

### 5.4 Configuration Changes

**File:** `backend/app/config.py`

```python
"""Application configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    app_name: str = "ArtifactX"
    debug: bool = False

    # PostgreSQL Database - Configure via environment variable
    # Format: postgresql://user:password@host:port/database
    database_url: str = "postgresql://artifactx:artifactx_password@localhost:5432/artifactx"

    upload_dir: str = "uploads"
    max_upload_size: int = 1073741824  # 1GB in bytes
    log_level: str = "INFO"

    # Demo mode
    demo_mode: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure data directories exist
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / settings.upload_dir
REPORTS_DIR = BASE_DIR / "reports"

DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
```

### 5.5 Database Configuration

**File:** `backend/app/database.py`

```python
"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from backend.app.config import settings

# PostgreSQL configuration with connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Yield a database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 5.6 Environment File

**File:** `.env.example` (create if not exists)

```bash
# Application
APP_NAME=ArtifactX
DEBUG=false
LOG_LEVEL=INFO

# Database - PostgreSQL
# Format: postgresql://username:password@host:port/database
DATABASE_URL=postgresql://artifactx:artifactx_password@localhost:5432/artifactx

# Demo mode (enable for testing)
DEMO_MODE=false

# File uploads
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE=1073741824
```

### 5.7 Model Updates for PostgreSQL

**File:** `backend/models/models.py`

Some adjustments may be needed:

```python
"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Index,  # Explicit index creation for PostgreSQL
)
from sqlalchemy.orm import relationship

from backend.app.database import Base


# Add explicit indexes for PostgreSQL optimization
# PostgreSQL handles indexes differently than SQLite

class Case(Base):
    """Forensic case."""

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    investigator = Column(String(255))
    status = Column(String(50), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add indexes for common queries
    __table_args__ = (
        Index('ix_cases_status', 'status'),
        Index('ix_cases_created_at', 'created_at'),
    )

    # Relationships remain the same
    evidence_items = relationship(
        "Evidence", back_populates="case", cascade="all, delete"
    )
    # ... rest of model
```

### 5.8 Database Setup Script

**Create:** `backend/scripts/setup_postgres.sh`

```bash
#!/bin/bash
# PostgreSQL setup script for ArtifactX

# Variables - update these for your environment
DB_NAME="artifactx"
DB_USER="artifactx"
DB_PASSWORD="artifactx_password"
DB_HOST="localhost"
DB_PORT="5432"

echo "Setting up PostgreSQL database for ArtifactX..."

# Create database if it doesn't exist
psql -U postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Database $DB_NAME may already exist"

# Create user if it doesn't exist
psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "User $DB_USER may already exist"

# Grant privileges
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
psql -U postgres -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

# Set default privileges for future tables
psql -U postgres -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;"
psql -U postgres -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;"

echo "PostgreSQL setup complete!"
echo "Update your .env file with:"
echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
```

**Create:** `backend/scripts/setup_postgres.sql`

```sql
-- PostgreSQL setup script for ArtifactX
-- Run: psql -U postgres -d artifactx -f setup_postgres.sql

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for performance (run after initial migration)
-- Message queries
CREATE INDEX IF NOT EXISTS ix_wa_messages_timestamp ON wa_messages (timestamp);
CREATE INDEX IF NOT EXISTS ix_wa_messages_key_remote_jid ON wa_messages (key_remote_jid);
CREATE INDEX IF NOT EXISTS ix_tg_messages_timestamp ON tg_messages (timestamp);
CREATE INDEX IF NOT EXISTS ix_tg_messages_dialog_id ON tg_messages (dialog_id);

-- Timeline events
CREATE INDEX IF NOT EXISTS ix_timeline_events_normalized_timestamp ON timeline_events (normalized_timestamp);
CREATE INDEX IF NOT EXISTS ix_timeline_events_source_app ON timeline_events (source_app);

-- Correlation edges
CREATE INDEX IF NOT EXISTS ix_correlation_edges_case_id ON correlation_edges (case_id);

-- Deleted messages
CREATE INDEX IF NOT EXISTS ix_deleted_messages_case_id ON deleted_messages (case_id);
CREATE INDEX IF NOT EXISTS ix_deleted_messages_source_app ON deleted_messages (source_app);

-- Error logs (high volume table)
CREATE INDEX IF NOT EXISTS ix_error_logs_case_id ON error_logs (case_id);
CREATE INDEX IF NOT EXISTS ix_error_logs_evidence_id ON error_logs (evidence_id);
CREATE INDEX IF NOT EXISTS ix_error_logs_timestamp ON error_logs (timestamp DESC);
```

### 5.9 Docker Compose for PostgreSQL (Optional)

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: artifactx-postgres
    environment:
      POSTGRES_DB: artifactx
      POSTGRES_USER: artifactx
      POSTGRES_PASSWORD: artifactx_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/setup_postgres.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U artifactx -d artifactx"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: artifactx-backend
    environment:
      DATABASE_URL: postgresql://artifactx:artifactx_password@postgres:5432/artifactx
      DEBUG: "false"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./uploads:/app/uploads
      - ./reports:/app/reports
      - ./data:/app/data

  frontend:
    build:
      context: frontend
      dockerfile: Dockerfile
    container_name: artifactx-frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### 5.10 Database Migrations with Alembic

Since ArtifactX now uses PostgreSQL only, use Alembic for database migrations:

**Install alembic:**
```bash
pip install alembic
cd backend
alembic init migrations
```

**Configure alembic.ini:**
```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://artifactx:artifactx_password@localhost:5432/artifactx
```

**Generate initial migration:**
```bash
cd backend
alembic revision --autogenerate -m "Initial migration"
```

### 5.11 Verification Steps

After migration:

1. **Test connections:**
   ```bash
   # Test PostgreSQL connection
   psql -U artifactx -d artifactx -c "SELECT 1;"
   
   # Test application
   cd backend && uvicorn app.main:app --reload
   curl http://localhost:8000/api/health
   ```

2. **Verify tables:**
   ```sql
   -- List all tables
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
   
   -- Get row counts
   SELECT 'cases' as table, COUNT(*) as count FROM cases
   UNION ALL SELECT 'evidence', COUNT(*) FROM evidence
   UNION ALL SELECT 'wa_messages', COUNT(*) FROM wa_messages;
   ```

3. **Check indexes:**
   ```sql
   SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public';
   ```

### 5.12 Troubleshooting

**Issue:** `connection refused` error
- Solution: Ensure PostgreSQL is running and accepting connections
  ```bash
  # Linux
  sudo systemctl start postgresql
  sudo systemctl status postgresql
  
  # macOS
  brew services start postgresql
  ```

**Issue:** `permission denied for table`
- Solution: Grant permissions to user
  ```sql
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO artifactx;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO artifactx;
  ```

**Issue:** `psycopg2.errors.UniqueViolation`
- Solution: Clear PostgreSQL database and re-run migration
  ```sql
  DROP SCHEMA public CASCADE;
  CREATE SCHEMA public;
  ```

### 5.13 Performance Considerations

- Use connection pooling (already configured in database.py)
- Create indexes on frequently queried columns
- Consider partitioning large tables (messages, logs) by date
- Use `pg_stat_statements` for query analysis

```sql
-- Enable pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## Priority Order

1. **Critical:** Fix `DeletedMessage` import error
2. **High:** Add demo mode functionality
3. **High:** PostgreSQL migration for production
4. **Medium:** Improve error handling and null checks
5. **Low:** Add utility components (ErrorBoundary, LoadingSpinner)

---

## Notes

- All forensic analysis must still parse from actual uploaded evidence files
- Demo mode is for UI/UX testing only
- Ensure demo data doesn't persist in production
- PostgreSQL is recommended for multi-user production environments
- Always backup data before migration