"""Unit tests for domain entities — pure business logic, no IO."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.conversations.entities import Conversation, Message
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole
from src.domain.documents.entities import Chunk, Document
from src.domain.documents.value_objects import DocumentMimeType
from src.domain.llm_usage.entities import TokenUsage
from src.domain.questions.entities import Question
from src.domain.questions.value_objects import QuestionStatus
from src.domain.shared.exceptions import InvalidOperationError
from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenants.entities import Tenant
from src.domain.tenants.value_objects import TenantStatus
from src.domain.users.entities import User, UserTenant

# ── Tenant ──────────────────────────────────────────────────────────


def test_tenant_create_emits_event() -> None:
    t = Tenant.create(name="Acme", slug="acme")
    assert t.is_new
    assert t.status == TenantStatus.ACTIVE
    assert len(t.pending_events) == 1


def test_tenant_suspend_and_activate() -> None:
    t = Tenant.create(name="X", slug="xx")
    t.suspend()
    assert t.status == TenantStatus.SUSPENDED
    t.activate()
    assert t.status == TenantStatus.ACTIVE  # type: ignore[comparison-overlap]


def test_tenant_double_suspend_raises() -> None:
    t = Tenant.create(name="X", slug="xx")
    t.suspend()
    with pytest.raises(InvalidOperationError):
        t.suspend()


def test_tenant_rename() -> None:
    t = Tenant.create(name="Old", slug="old")
    t.rename("New Name")
    assert t.name == "New Name"


def test_tenant_rename_empty_raises() -> None:
    t = Tenant.create(name="X", slug="xx")
    with pytest.raises(InvalidOperationError):
        t.rename("   ")


# ── User ────────────────────────────────────────────────────────────


def test_user_create_normalizes_email() -> None:
    u = User.create(email="  Test@Example.COM  ", hashed_password="hash")
    assert u.email == "test@example.com"
    assert u.is_new


def test_user_deactivate_and_activate() -> None:
    u = User.create(email="a@b.com", hashed_password="h")
    u.deactivate()
    assert not u.is_active
    u.activate()
    assert u.is_active


def test_user_tenant_create() -> None:
    ut = UserTenant.create(user_id=uuid4(), tenant_id=uuid4())
    assert ut.is_new
    assert ut.role.value == "owner"


# ── Conversation + Message ──────────────────────────────────────────


def test_conversation_start_emits_event() -> None:
    c = Conversation.start(tenant_id=uuid4(), thread_id="t1", channel=ConversationChannel.WEB)
    assert c.is_new
    assert len(c.pending_events) == 1


def test_conversation_touch_updates_timestamps() -> None:
    c = Conversation.start(tenant_id=uuid4(), thread_id="t2", channel=ConversationChannel.API)
    old_updated = c.updated_at
    c.touch()
    assert c.updated_at >= old_updated
    assert c.last_message_at is not None


def test_message_create() -> None:
    m = Message.create(
        conversation_id=uuid4(),
        tenant_id=uuid4(),
        role=ConversationRole.USER,
        content="Hello",
    )
    assert m.is_new
    assert m.role == ConversationRole.USER


# ── Document + Chunk ────────────────────────────────────────────────


def test_document_lifecycle() -> None:
    d = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="notes.pdf",
        mime_type=DocumentMimeType.PDF,
        size_bytes=1024,
    )
    assert d.is_new
    d.mark_ingesting()
    assert d.status.value == "ingesting"
    d.mark_ready(chunk_count=10)
    assert d.chunk_count == 10


def test_document_mark_failed() -> None:
    d = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=None,
        filename="bad.pdf",
        mime_type=DocumentMimeType.PDF,
        size_bytes=100,
    )
    d.mark_ingesting()
    d.mark_failed(reason="Parse error")
    assert d.status.value == "failed"
    assert d.error == "Parse error"


def test_chunk_create() -> None:
    c = Chunk.create(
        document_id=uuid4(),
        tenant_id=uuid4(),
        chunk_index=0,
        content="text",
        embedding=[0.1] * 10,
    )
    assert c.is_new


# ── TokenUsage ──────────────────────────────────────────────────────


def test_token_usage_record_calculates_cost() -> None:
    u = TokenUsage.record(
        tenant_id=uuid4(),
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=1000,
        output_tokens=500,
    )
    assert u.total_cost > 0
    assert u.is_new


# ── Question ────────────────────────────────────────────────────────


def test_question_submit_and_resolve() -> None:
    q = Question.submit(
        tenant_id=uuid4(),
        channel=ConversationChannel.WHATSAPP,
        question_text="Office hours?",
        contact_id=uuid4(),
    )
    assert q.status == QuestionStatus.SUBMITTED
    q.resolve(reply="9-5 Sun-Thu", replied_by_user_id=uuid4())
    assert q.status == QuestionStatus.RESOLVED  # type: ignore[comparison-overlap]
    assert q.owner_reply == "9-5 Sun-Thu"


def test_question_double_resolve_raises() -> None:
    q = Question.submit(
        tenant_id=uuid4(),
        channel=ConversationChannel.WEB,
        question_text="Hi",
    )
    q.resolve(reply="Hello", replied_by_user_id=uuid4())
    with pytest.raises(InvalidOperationError):
        q.resolve(reply="Again", replied_by_user_id=uuid4())


def test_question_close() -> None:
    q = Question.submit(
        tenant_id=uuid4(),
        channel=ConversationChannel.TELEGRAM,
        question_text="Spam",
    )
    q.close()
    assert q.status == QuestionStatus.CLOSED


def test_question_empty_text_raises() -> None:
    with pytest.raises(InvalidOperationError):
        Question.submit(
            tenant_id=uuid4(),
            channel=ConversationChannel.WEB,
            question_text="  ",
        )


def test_question_empty_reply_raises() -> None:
    q = Question.submit(
        tenant_id=uuid4(),
        channel=ConversationChannel.WEB,
        question_text="Q",
    )
    with pytest.raises(InvalidOperationError):
        q.resolve(reply="   ", replied_by_user_id=uuid4())


# ── TenantConfig ────────────────────────────────────────────────────


def test_tenant_config_create_default() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    assert c.llm_provider.value == "openai"
    assert c.bot_name == "Front Desk Assistant"


def test_tenant_config_mask_key() -> None:
    assert TenantConfig.mask_key("sk-1234567890abcdef") == "****cdef"
    assert TenantConfig.mask_key("short") == "****"
    assert TenantConfig.mask_key("") == ""
    assert TenantConfig.mask_key(None) == ""


def test_tenant_config_update_llm() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.update_llm(provider=None, model="claude-sonnet-4-5", api_key="sk-test")
    assert c.llm_model == "claude-sonnet-4-5"
    assert c.llm_api_key == "sk-test"


def test_tenant_config_update_whatsapp() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.update_whatsapp(phone_number_id="12345")
    assert c.whatsapp_phone_number_id == "12345"


def test_tenant_config_update_bot() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.update_bot(name="MyBot", language="ar")
    assert c.bot_name == "MyBot"
    assert c.bot_language == "ar"
