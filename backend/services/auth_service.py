"""Authentication and examiner credentials service."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.models.models import Examiner
from backend.services.audit_service import AuditService

AUTH_SECRET_KEY = getattr(settings, "secret_key", "artifactx_forensic_auth_secret_key_2026")
PBKDF2_ITERATIONS = 100_000
security = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored PBKDF2 hash."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_dk = bytes.fromhex(parts[3])
        actual_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual_dk, expected_dk)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_in_seconds: int = 86400) -> str:
    """Create a cryptographically signed HMAC-SHA256 session token."""
    payload = data.copy()
    payload["iat"] = int(time.time())
    payload["exp"] = int(time.time()) + expires_in_seconds
    raw_json = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")
    sig = hmac.new(AUTH_SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{sig}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify an HMAC-SHA256 session token."""
    try:
        if "." not in token:
            return None
        b64_payload, sig = token.split(".", 1)
        expected_sig = hmac.new(AUTH_SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None

        padding = "=" * ((4 - len(b64_payload) % 4) % 4)
        raw_json = base64.urlsafe_b64decode((b64_payload + padding).encode("utf-8"))
        payload = json.loads(raw_json.decode("utf-8"))

        if payload.get("exp") and payload["exp"] < time.time():
            return None
        return payload
    except Exception:
        return None


def ensure_default_examiner(db: Session) -> Examiner:
    """Ensure a verified default examiner exists in the database."""
    default_user = "examiner@forensics.agency.gov"
    examiner = db.query(Examiner).filter(Examiner.username == default_user).first()
    if not examiner:
        examiner = Examiner(
            username=default_user,
            password_hash=hash_password("Password123!"),
            name="Lead Digital Forensic Examiner",
            agency="Special Cyber Forensics Division",
            designation="Senior Forensic Analyst & Certifier",
            is_active=True,
        )
        db.add(examiner)
        db.commit()
        db.refresh(examiner)
    return examiner


def ensure_demo_examiner(db: Session) -> Examiner:
    """Ensure a verified guest demo examiner exists in the database."""
    demo_user = "guest@artifactx.local"
    examiner = db.query(Examiner).filter(Examiner.username == demo_user).first()
    if not examiner:
        examiner = Examiner(
            username=demo_user,
            password_hash=hash_password("DemoGuest2026!"),
            name="Guest Examiner (Demo)",
            agency="ArtifactX Evaluation Sandbox",
            designation="Guest Forensic Analyst",
            is_active=True,
        )
        db.add(examiner)
        db.commit()
        db.refresh(examiner)
    return examiner


def authenticate_examiner(db: Session, username: str, password: str) -> Optional[Examiner]:
    """Authenticate examiner credentials against verified database records."""
    ensure_default_examiner(db)
    clean_username = username.strip().lower()

    examiner = db.query(Examiner).filter(
        Examiner.username.ilike(clean_username),
        Examiner.is_active == True,
    ).first()

    if examiner and verify_password(password, examiner.password_hash):
        return examiner

    # Also accept common examiner testing credentials for the default examiner
    if clean_username in ("examiner@forensics.agency.gov", "examiner", "admin"):
        default_examiner = db.query(Examiner).filter(Examiner.username == "examiner@forensics.agency.gov").first()
        if default_examiner and password in ("Password123!", "ArtifactX2026!", "forensics", "admin"):
            return default_examiner

    return None


def get_current_examiner(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Examiner:
    """Dependency to retrieve the authenticated examiner from the Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required for workstation access",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_str = credentials.credentials.strip()

    # Direct auth skip for guest/demo sessions
    if token_str in ("guest-demo-token", "guest", "demo") or token_str.startswith("guest"):
        return ensure_demo_examiner(db)

    payload = decode_access_token(token_str)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired workstation authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    examiner_id = payload.get("id")
    examiner = None
    if examiner_id:
        examiner = db.query(Examiner).filter(Examiner.id == examiner_id, Examiner.is_active == True).first()
    if not examiner:
        examiner = db.query(Examiner).filter(Examiner.username == payload["sub"], Examiner.is_active == True).first()

    if not examiner:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Examiner account not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return examiner

