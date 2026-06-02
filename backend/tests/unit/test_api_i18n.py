"""Unit tests for API-boundary localization helpers."""

from __future__ import annotations

from src.drivers.api.i18n import resolve_locale, translate


def test_resolve_locale_defaults_to_en() -> None:
    assert resolve_locale(None) == "en"
    assert resolve_locale("") == "en"
    assert resolve_locale("fr,de;q=0.8") == "en"


def test_resolve_locale_picks_supported() -> None:
    assert resolve_locale("ar") == "ar"
    assert resolve_locale("ar-EG,en;q=0.8") == "ar"
    assert resolve_locale("en-US,en;q=0.9") == "en"
    assert resolve_locale("AR") == "ar"


def test_translate_english_returns_default() -> None:
    # English is the source message — never pulled from the catalog.
    assert translate("auth.invalid_credentials", "en", "Invalid email or password") == "Invalid email or password"


def test_translate_arabic_uses_catalog() -> None:
    out = translate("auth.invalid_credentials", "ar", "Invalid email or password")
    assert out != "Invalid email or password"
    assert out  # non-empty Arabic string


def test_translate_unknown_code_or_none_falls_back() -> None:
    assert translate("nope.unknown", "ar", "fallback") == "fallback"
    assert translate(None, "ar", "fallback") == "fallback"
