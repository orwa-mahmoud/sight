"""Admin API v1 — platform super-admin endpoints."""

from src.drivers.api.v1.admin.routes import router as admin_router

__all__ = ["admin_router"]
