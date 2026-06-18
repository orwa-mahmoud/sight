"""Unit tests for the document upload handler's pre-buffer guards."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import BackgroundTasks, HTTPException

from src.drivers.api.v1.documents.routes import _MAX_UPLOAD_BYTES, upload_document


@pytest.mark.asyncio
async def test_rejects_oversized_upload_before_reading_body() -> None:
    file = MagicMock()
    file.filename = "big.pdf"
    file.size = _MAX_UPLOAD_BYTES + 1
    file.read = AsyncMock()  # must not be called — we reject before buffering

    with pytest.raises(HTTPException) as exc:
        await upload_document(current_user=MagicMock(), uow=MagicMock(), background_tasks=BackgroundTasks(), file=file)

    assert exc.value.status_code == 413
    file.read.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_missing_filename() -> None:
    file = MagicMock()
    file.filename = ""

    with pytest.raises(HTTPException) as exc:
        await upload_document(current_user=MagicMock(), uow=MagicMock(), background_tasks=BackgroundTasks(), file=file)

    assert exc.value.status_code == 400
