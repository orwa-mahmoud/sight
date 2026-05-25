"""Unit tests for notification context_loader — RecipientInfo + CONTEXT_LOADERS registry."""

from __future__ import annotations

from src.infrastructure.notifications.context_loader import CONTEXT_LOADERS, RecipientInfo


class TestRecipientInfo:
    def test_construction_and_fields(self) -> None:
        info = RecipientInfo(
            id="r-1",
            name="Alice",
            phone="+1234567890",
            telegram_user_id="tg_alice",
        )
        assert info.id == "r-1"
        assert info.name == "Alice"
        assert info.phone == "+1234567890"
        assert info.telegram_user_id == "tg_alice"

    def test_optional_fields_accept_none(self) -> None:
        info = RecipientInfo(id="r-2", name=None, phone=None, telegram_user_id=None)
        assert info.name is None
        assert info.phone is None
        assert info.telegram_user_id is None

    def test_frozen_dataclass(self) -> None:
        info = RecipientInfo(id="r-3", name="Bob", phone=None, telegram_user_id=None)
        try:
            info.name = "Hacked"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # expected: frozen

    def test_equality(self) -> None:
        a = RecipientInfo(id="x", name="A", phone=None, telegram_user_id=None)
        b = RecipientInfo(id="x", name="A", phone=None, telegram_user_id=None)
        assert a == b

    def test_inequality(self) -> None:
        a = RecipientInfo(id="x", name="A", phone=None, telegram_user_id=None)
        b = RecipientInfo(id="y", name="A", phone=None, telegram_user_id=None)
        assert a != b


class TestContextLoaders:
    def test_registry_is_initially_empty(self) -> None:
        assert isinstance(CONTEXT_LOADERS, dict)
        assert len(CONTEXT_LOADERS) == 0
