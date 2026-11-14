"""Pydantic schemas for authentication and examiner credentials."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Examiner username, email, or badge ID")
    password: str = Field(..., description="Workstation PIN or passphrase")


class ExaminerRead(BaseModel):
    id: int
    username: str
    name: str
    agency: str
    designation: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    examiner: ExaminerRead


class ExaminerMeResponse(BaseModel):
    examiner: ExaminerRead

