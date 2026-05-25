"""Unit tests for i18n."""

from __future__ import annotations

from src.ai.context.i18n import translate


def test_english_default():
    assert translate("welcome") == "Hello! How can I help you today?"


def test_arabic():
    assert "مرحبًا" in translate("welcome", "ar")


def test_french():
    assert "Bonjour" in translate("welcome", "fr")


def test_unknown_language_fallback():
    assert translate("welcome", "xx") == "Hello! How can I help you today?"


def test_unknown_key():
    assert translate("nonexistent") == "nonexistent"


def test_escalation_spanish():
    assert "equipo" in translate("escalation_notice", "es")
