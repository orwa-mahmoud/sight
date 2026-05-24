"""API v1 root router — aggregates feature routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from src.drivers.api.v1.auth import auth_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
