"""Examiner authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.models.models import Examiner
from backend.schemas.auth import ExaminerMeResponse, ExaminerRead, LoginRequest, LoginResponse
from backend.services.audit_service import AuditService
from backend.services.auth_service import (
    authenticate_examiner,
    create_access_token,
    ensure_demo_examiner,
    get_current_examiner,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate examiner credentials and return session token."""
    examiner = authenticate_examiner(db, request.username, request.password)
    if not examiner:
        try:
            AuditService.append(
                db=db,
                action="EXAMINER_LOGIN_FAILED",
                actor=request.username,
                details={"username": request.username, "reason": "Invalid credentials"},
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Examiner ID or authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        {
            "sub": examiner.username,
            "id": examiner.id,
            "name": examiner.name,
            "agency": examiner.agency,
            "designation": examiner.designation,
        }
    )

    try:
        AuditService.append(
            db=db,
            action="EXAMINER_LOGIN_SUCCESS",
            actor=examiner.username,
            details={
                "examiner_id": examiner.id,
                "name": examiner.name,
                "agency": examiner.agency,
            },
        )
    except Exception:
        pass

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        examiner=ExaminerRead.model_validate(examiner),
    )


@router.post("/guest", response_model=LoginResponse)
def login_as_guest(db: Session = Depends(get_db)):
    """Authenticate as a guest/demo examiner and return a valid session token."""
    examiner = ensure_demo_examiner(db)
    token = create_access_token(
        {
            "sub": examiner.username,
            "id": examiner.id,
            "name": examiner.name,
            "agency": examiner.agency,
            "designation": examiner.designation,
        }
    )
    try:
        AuditService.append(
            db=db,
            action="EXAMINER_LOGIN_GUEST",
            actor=examiner.username,
            details={
                "examiner_id": examiner.id,
                "name": examiner.name,
                "role": "guest_demo",
            },
        )
    except Exception:
        pass

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        examiner=ExaminerRead.model_validate(examiner),
    )


@router.get("/me", response_model=ExaminerMeResponse)
def get_current_user_profile(examiner: Examiner = Depends(get_current_examiner)):
    """Validate active authorization token and return examiner profile."""
    return ExaminerMeResponse(examiner=ExaminerRead.model_validate(examiner))

