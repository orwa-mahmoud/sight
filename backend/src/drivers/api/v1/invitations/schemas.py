"""Pydantic schemas for the invitations endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateInvitationRequest(BaseModel):
    email: EmailStr


class InvitationResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    status: str
    token: str
    invite_url: str
    expires_at: datetime
    created_at: datetime


class InvitationPreviewResponse(BaseModel):
    tenant_name: str
    email: EmailStr
    role: str
    status: str
    valid: bool


class RegisterViaInvitationRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
