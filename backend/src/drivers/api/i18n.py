"""API-boundary localization of user-facing messages.

English is the source: domain errors carry their English `message`, and only
non-English overrides live in `_CATALOG`, keyed by a stable `code`. The locale
is resolved per request from the `Accept-Language` header. If a code has no
catalog entry for the resolved locale, the English message is returned — so
adding i18n never changes existing English responses.

Scope: `DomainError` messages (business errors). Pydantic 422 validation
messages are out of scope for now.
"""

from __future__ import annotations

SUPPORTED_LOCALES = ("en", "ar")
DEFAULT_LOCALE = "en"

# code -> { locale -> translated string }. English omitted on purpose (it comes
# from the raised message). Add codes at raise sites to localize a message.
_CATALOG: dict[str, dict[str, str]] = {
    "error.generic": {"ar": "حدث خطأ"},
    "auth.invalid_credentials": {"ar": "البريد الإلكتروني أو كلمة المرور غير صحيحة"},
    "auth.no_tenant": {"ar": "المستخدم غير مرتبط بأي مستأجر"},
    "auth.current_password_incorrect": {"ar": "كلمة المرور الحالية غير صحيحة"},
    "auth.email_taken": {"ar": "يوجد مستخدم بهذا البريد الإلكتروني بالفعل"},
    "auth.slug_taken": {"ar": "معرّف المستأجر مستخدم بالفعل"},
    "user.not_found": {"ar": "المستخدم غير موجود"},
    "document.not_found": {"ar": "المستند غير موجود"},
    "document.forbidden": {"ar": "المستند لا يخص هذا المستأجر"},
    "document.unsupported_type": {"ar": "نوع ملف غير مدعوم. المسموح: PDF وDOCX وMarkdown ونص عادي."},
    "question.not_found": {"ar": "السؤال غير موجود"},
    "question.forbidden": {"ar": "السؤال لا يخص هذا المستأجر"},
}


def resolve_locale(accept_language: str | None) -> str:
    """Pick the best supported locale from an `Accept-Language` header value."""
    if not accept_language:
        return DEFAULT_LOCALE
    for part in accept_language.split(","):
        tag = part.split(";", 1)[0].strip().lower()
        primary = tag.split("-", 1)[0]
        if primary in SUPPORTED_LOCALES:
            return primary
    return DEFAULT_LOCALE


def translate(code: str | None, locale: str, default: str) -> str:
    """Localized string for `code` in `locale`, falling back to `default` (English)."""
    if not code or locale == DEFAULT_LOCALE:
        return default
    return _CATALOG.get(code, {}).get(locale, default)
