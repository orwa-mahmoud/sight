"""Notification failure repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.notifications.entities import NotificationFailure


class NotificationFailureRepository(ABC):
    """Port for persisting notification failures."""

    @abstractmethod
    async def save(self, failure: NotificationFailure) -> None: ...
