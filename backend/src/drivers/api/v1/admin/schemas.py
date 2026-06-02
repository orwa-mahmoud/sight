"""Pydantic schemas for the platform-admin endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr


class AdminTenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    owner_email: EmailStr | None
    user_count: int
    document_count: int


class AdminUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_platform_admin: bool
    tenant_id: UUID | None
    tenant_name: str | None
    role: str | None


class TenantStatusResponse(BaseModel):
    id: UUID
    status: str


class UserActiveResponse(BaseModel):
    id: UUID
    is_active: bool
