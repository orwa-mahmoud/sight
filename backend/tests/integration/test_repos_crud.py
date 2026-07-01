"""Integration tests for repository CRUD — covers the save/update paths."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.entities import Conversation
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentMimeType
from src.domain.llm_usage.entities import TokenUsage as TokenUsageEntity
from src.domain.questions.entities import Question
from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenants.entities import Tenant
from src.domain.users.entities import User, UserTenant
from src.domain.users.value_objects import UserTenantRole
from src.infrastructure.persistence.postgres.database import async_session_factory


async def _make_tenant_and_user() -> tuple:  # type: ignore[type-arg]
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="CRUD Test", slug=f"crud-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        user = User.create(email=f"{uuid4().hex[:8]}@test.com", hashed_password="hash")
        await uow.users.save(user)
        await uow.flush()
        link = UserTenant.create(user_id=user.id, tenant_id=tenant.id, role=UserTenantRole.OWNER)
        await uow.user_tenants.save(link)
        config = TenantConfig.create_default(tenant_id=tenant.id)
        config._is_new = True
        await uow.tenant_configs.save(config)
        await uow.commit()
        return tenant, user, link, config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_update_path(client: None) -> None:
    tenant, _, _, _ = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.tenants.get_by_id(tenant.id)
        assert loaded is not None
        loaded.rename("Updated Name")
        await uow.tenants.save(loaded)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        reloaded = await uow.tenants.get_by_id(tenant.id)
        assert reloaded is not None
        assert reloaded.name == "Updated Name"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_get_by_slug(client: None) -> None:
    tenant, _, _, _ = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        found = await uow.tenants.get_by_slug(tenant.slug)
        assert found is not None
        assert found.id == tenant.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_list_all(client: None) -> None:
    await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenants = await uow.tenants.list_all()
        assert len(tenants) >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_update_and_get_by_email(client: None) -> None:
    _, user, _, _ = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.users.get_by_id(user.id)
        assert loaded is not None
        loaded.update_password("new-hash")
        await uow.users.save(loaded)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        by_email = await uow.users.get_by_email(user.email)
        assert by_email is not None
        assert by_email.hashed_password == "new-hash"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_tenant_get_and_list(client: None) -> None:
    tenant, user, link, _ = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        found = await uow.user_tenants.get(user.id, tenant.id)
        assert found is not None
        assert found.id == link.id
        all_links = await uow.user_tenants.list_for_user(user.id)
        assert len(all_links) >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_config_update(client: None) -> None:
    _, _, _, config = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.tenant_configs.get_by_tenant_id(config.tenant_id)
        assert loaded is not None
        loaded.update_llm(api_key="sk-new-key")
        await uow.tenant_configs.save(loaded)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        reloaded = await uow.tenant_configs.get_by_tenant_id(config.tenant_id)
        assert reloaded is not None
        assert reloaded.llm_api_key == "sk-new-key"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_config_long_encrypted_secrets_round_trip(client: None) -> None:
    """Max-length (255-char) app_secret / webhook_secret encrypt to ~424 chars — the
    columns must be Text, not varchar(255), or the save 500s on overflow."""
    _, _, _, config = await _make_tenant_and_user()
    long_app_secret = "a" * 255
    long_webhook_secret = "b" * 255
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.tenant_configs.get_by_tenant_id(config.tenant_id)
        assert loaded is not None
        loaded.update_whatsapp(app_secret=long_app_secret)
        loaded.update_telegram(webhook_secret=long_webhook_secret)
        await uow.tenant_configs.save(loaded)
        await uow.commit()  # would raise StringDataRightTruncation on varchar(255)
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        reloaded = await uow.tenant_configs.get_by_tenant_id(config.tenant_id)
        assert reloaded is not None
        assert reloaded.whatsapp_app_secret == long_app_secret  # decrypts back intact
        assert reloaded.telegram_webhook_secret == long_webhook_secret


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_usage_list_and_aggregate(client: None) -> None:
    tenant, _, _, _ = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        u1 = TokenUsageEntity.record(
            tenant_id=tenant.id,
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
        )
        u2 = TokenUsageEntity.record(
            tenant_id=tenant.id,
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=200,
            output_tokens=100,
        )
        await uow.token_usages.save(u1)
        await uow.token_usages.save(u2)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        rows = await uow.token_usages.list_for_tenant(tenant.id)
        assert len(rows) == 2
        stats = await uow.token_usages.aggregate_for_tenant(tenant.id)
        assert stats.total_calls == 2
        assert stats.total_input_tokens == 300


@pytest.mark.integration
@pytest.mark.asyncio
async def test_question_list_filter_and_count(client: None) -> None:
    tenant, _, _, _ = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        q = Question.submit(tenant_id=tenant.id, channel=ConversationChannel.WEB, question_text="Q1")
        await uow.questions.save(q)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        from src.domain.questions.value_objects import QuestionStatus

        all_q = await uow.questions.list_for_tenant(tenant.id)
        assert len(all_q) == 1
        count = await uow.questions.count_for_tenant(tenant.id, status=QuestionStatus.SUBMITTED)
        assert count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_crud(client: None) -> None:
    tenant, user, _, _ = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        doc = Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=user.id,
            filename="test.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=100,
        )
        await uow.documents.save(doc)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.documents.get_by_id(doc.id)
        assert loaded is not None
        docs = await uow.documents.list_for_tenant(tenant.id)
        assert len(docs) == 1
        await uow.documents.delete(doc.id)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        assert await uow.documents.get_by_id(doc.id) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_update_path(client: None) -> None:
    tenant, _, _, _ = await _make_tenant_and_user()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        conv = Conversation.start(
            tenant_id=tenant.id,
            thread_id=f"t-{uuid4().hex[:8]}",
            channel=ConversationChannel.API,
        )
        await uow.conversations.save(conv)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.conversations.get_by_id(conv.id)
        assert loaded is not None
        loaded.touch()
        await uow.conversations.save(loaded)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        reloaded = await uow.conversations.get_by_id(conv.id)
        assert reloaded is not None
        assert reloaded.last_message_at is not None
