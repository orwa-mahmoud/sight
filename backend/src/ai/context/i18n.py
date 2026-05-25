"""Simple i18n for bot messages — lookup by language code."""

from __future__ import annotations

_MESSAGES: dict[str, dict[str, str]] = {
    "escalation_notice": {
        "en": "Let me check with the team and get back to you.",
        "ar": "دعني أتحقق مع الفريق وأعود إليك.",
        "fr": "Laissez-moi vérifier avec l'équipe et je reviens vers vous.",
        "es": "Déjame consultar con el equipo y te respondo.",
    },
    "welcome": {
        "en": "Hello! How can I help you today?",
        "ar": "مرحبًا! كيف يمكنني مساعدتك اليوم؟",
        "fr": "Bonjour ! Comment puis-je vous aider ?",
        "es": "¡Hola! ¿En qué puedo ayudarte?",
    },
    "still_working": {
        "en": "Still working on it — one moment please.",
        "ar": "ما زلت أعمل على طلبك — لحظة من فضلك.",
        "fr": "Je m'en occupe — un instant s'il vous plaît.",
        "es": "Sigo trabajando en ello — un momento por favor.",
    },
}


def translate(key: str, language: str = "en") -> str:
    messages = _MESSAGES.get(key, {})
    return messages.get(language, messages.get("en", key))
