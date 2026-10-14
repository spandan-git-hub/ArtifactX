"""Audit log API endpoints (B5.5)."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.services.audit_service import AuditService

router = APIRouter()


@router.get("/verify")
def verify_audit_trail(
    case_id: Optional[int] = Query(None, description="Optional case ID to filter or verify"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Verify the cryptographic integrity of the hash-chained audit log.
    Recomputes SHA-256 for all entries from genesis to head.
    """
    result = AuditService.verify_audit_chain(db, case_id=case_id)
    return result.to_dict()
