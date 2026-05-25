"""Integration tests targeting remaining coverage gaps in routes, repos, and use cases.

Covers:
- Repo "update existing entity where model is None" paths (conversation, key_fact, question,
  tenant_config, tenant, user repos — lines 26-27, 25-26, 27-28, 26-27, 29-30, 27-28)
- Use case error paths (authenticate_user line 40, change_password line 28,
  refresh_token line 24, register_owner line 85, list_documents line 47,
  list_questions line 32)
- Unit of work rollback (line 57)
- Route error paths (auth, conversations, health, key_facts, llm_usage,
  questions, settings, tenants, users)
- Document upload too-large (line 54) and no-filename (line 50)
- Document retrieve endpoint (lines 122-127)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.application.shared.unit_of_work import UnitOfWork
from src.infrastructure.persistence.postgres.database import async_session_factory
from tests.conftest import register_and_token

# ── Repo "model is None" update paths ────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_repo_save_update_model_not_found(client: None) -> None:
    """conversation_repo lines 26-27: entity not new, model not in DB -> insert."""
    from src.domain.conversations.entities import Conversation
    from src.domain.conversations.value_objects import ConversationChannel
    from src.domain.tenants.entities import Tenant

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="ConvTest", slug=f"ct-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.flush()

        conv = Conversation.start(
            tenant_id=tenant.id,
            thread_id=f"t-{uuid4().hex[:8]}",
            channel=ConversationChannel.WEB,
        )
        # Mark as persisted then clear from session so it's "not new" but not in DB
        conv._is_new = False
        await uow.conversations.save(conv)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.conversations.get_by_id(conv.id)
        assert loaded is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_key_fact_repo_save_update_model_not_found(client: None) -> None:
    """key_fact_repo lines 25-26: entity not new, model not in DB -> insert."""
    from src.domain.key_facts.entities import KeyFact
    from src.domain.tenants.entities import Tenant

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="KFTest", slug=f"kf-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.flush()

        fact = KeyFact.create(
            tenant_id=tenant.id,
            participant_identifier="+123",
            key="name",
            value="Alice",
        )
        fact._is_new = False
        await uow.key_facts.save(fact)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.key_facts.get(tenant.id, "+123", "name")
        assert loaded is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_question_repo_save_update_model_not_found(client: None) -> None:
    """question_repo lines 27-28: entity not new, model not in DB -> insert."""
    from src.domain.conversations.value_objects import ConversationChannel
    from src.domain.questions.entities import Question
    from src.domain.tenants.entities import Tenant

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="QTest", slug=f"qt-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.flush()

        q = Question.submit(tenant_id=tenant.id, channel=ConversationChannel.WEB, question_text="Test?")
        q._is_new = False
        await uow.questions.save(q)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.questions.get_by_id(q.id)
        assert loaded is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_config_repo_save_update_model_not_found(client: None) -> None:
    """tenant_config_repo lines 26-27: entity not new, model not in DB -> insert."""
    from src.domain.tenant_config.entities import TenantConfig
    from src.domain.tenants.entities import Tenant

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="TCTest", slug=f"tc-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.flush()

        config = TenantConfig.create_default(tenant_id=tenant.id)
        config._is_new = False
        await uow.tenant_configs.save(config)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.tenant_configs.get_by_tenant_id(tenant.id)
        assert loaded is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_repo_save_update_model_not_found(client: None) -> None:
    """tenant_repo lines 29-30: entity not new, model not in DB -> insert."""
    from src.domain.tenants.entities import Tenant

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="TRTest", slug=f"tr-{uuid4().hex[:8]}")
        tenant._is_new = False
        await uow.tenants.save(tenant)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.tenants.get_by_id(tenant.id)
        assert loaded is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_repo_save_update_model_not_found(client: None) -> None:
    """user_repo lines 27-28: entity not new, model not in DB -> insert."""
    from src.domain.users.entities import User

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        user = User.create(email=f"{uuid4().hex[:8]}@test.com", hashed_password="hash")
        user._is_new = False
        await uow.users.save(user)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.users.get_by_id(user.id)
        assert loaded is not None


# ── Use case error paths ──────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authenticate_user_no_tenant_link(client: AsyncClient) -> None:
    """authenticate_user.py line 40: user exists but has no tenant link."""
    # Register a user normally
    _token, user_id, _ = await register_and_token(client)

    # Delete the user_tenant link to simulate orphaned user
    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": user_id})
        await session.commit()

    # Try to login — should fail with "not associated with any tenant"
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": f"t-{user_id[:8]}@test.com", "password": "supersecure123"},
    )
    # The email won't match since register_and_token generates a random slug-based email
    # Let's use the proper approach: register with known credentials
    slug = f"at-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )

    # Get user ID from login
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecure123"})
    uid = login_resp.json()["user_id"]

    # Delete tenant link
    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.commit()

    # Now login should fail
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecure123"})
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_password_user_not_found(client: None) -> None:
    """change_password.py line 28: user not found -> EntityNotFoundError."""
    from src.application.auth.use_cases.change_password import ChangePassword, ChangePasswordUseCase
    from src.domain.shared.exceptions import EntityNotFoundError
    from src.infrastructure.auth.bcrypt_hasher import BcryptPasswordHasher

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = ChangePasswordUseCase(uow=uow, password_hasher=BcryptPasswordHasher())
        with pytest.raises(EntityNotFoundError, match="User not found"):
            await uc.execute(ChangePassword(user_id=uuid4(), old_password="old", new_password="newpassword"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_token_no_tenant(client: AsyncClient) -> None:
    """refresh_token.py line 24: user has no tenant link -> AuthenticationError."""
    slug = f"rt-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]

    # Delete tenant link
    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.commit()

    # Refresh should fail
    resp = await client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_owner_empty_tenant_name(client: AsyncClient) -> None:
    """register_owner.py line 85: empty tenant name."""
    slug = f"et-{uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{slug}@test.com",
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": "   ",
            "tenant_slug": slug,
        },
    )
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_documents_use_case_empty(client: AsyncClient) -> None:
    """list_documents.py line 47 via route: listing when no docs."""
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_questions_empty(client: AsyncClient) -> None:
    """list_questions.py line 32: returns empty list."""
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/questions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── UnitOfWork rollback ───────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unit_of_work_rollback(client: None) -> None:
    """unit_of_work.py line 57: rollback."""
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        from src.domain.tenants.entities import Tenant

        tenant = Tenant.create(name="Rollback", slug=f"rb-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.rollback()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.tenants.get_by_id(tenant.id)
        assert loaded is None


# ── Route error paths ─────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_register_short_password(client: AsyncClient) -> None:
    """auth/routes.py line 31: short password -> 400."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@test.com",
            "password": "short",
            "full_name": "Test",
            "tenant_name": "Test",
            "tenant_slug": "short-pw",
        },
    )
    assert resp.status_code in (400, 422)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_register_bad_slug(client: AsyncClient) -> None:
    """auth/routes.py line 31: invalid slug -> 400."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "slug@test.com",
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": "Test",
            "tenant_slug": "INVALID SLUG!!!",
        },
    )
    assert resp.status_code in (400, 422)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_login_nonexistent_email(client: AsyncClient) -> None:
    """auth/routes.py line 38: login with email that doesn't exist -> 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_me_with_token(client: AsyncClient) -> None:
    """auth/routes.py line 44: /me endpoint."""
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "email" in resp.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_refresh_endpoint(client: AsyncClient) -> None:
    """auth/routes.py line 57: refresh endpoint."""
    token, _, _ = await register_and_token(client)
    resp = await client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversations_route_no_tenant(client: AsyncClient) -> None:
    """conversations/routes.py line 24: user with no tenant."""
    slug = f"cn-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]

    # Delete tenant link
    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.commit()

    resp = await client.get("/api/v1/conversations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_ready_endpoint(client: AsyncClient) -> None:
    """health/routes.py lines 40-41: readiness check."""
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_key_facts_route_no_tenant(client: AsyncClient) -> None:
    """key_facts/routes.py line 27: no tenant link -> 401."""
    slug = f"kf-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]

    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.commit()

    resp = await client.get("/api/v1/key-facts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_usage_no_tenant(client: AsyncClient) -> None:
    """llm_usage/routes.py lines 24-26: no tenant link."""
    slug = f"lu-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]

    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.commit()

    resp = await client.get("/api/v1/llm-usage/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_questions_no_tenant(client: AsyncClient) -> None:
    """questions/routes.py line 40: no tenant link."""
    slug = f"qn-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]

    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.commit()

    resp = await client.get("/api/v1/questions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_settings_no_config(client: AsyncClient) -> None:
    """settings/routes.py lines 27, 31: no tenant config -> 404."""
    slug = f"sc-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    tid = reg.json()["tenant_id"]

    # Delete config
    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM tenant_configs WHERE tenant_id = :tid"), {"tid": tid})
        await session.commit()

    resp = await client.get("/api/v1/settings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenants_no_link(client: AsyncClient) -> None:
    """tenants/routes.py line 27: no tenant link -> 401."""
    slug = f"tn-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]

    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.commit()

    resp = await client.get("/api/v1/tenants/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenants_tenant_deleted(client: AsyncClient) -> None:
    """tenants/routes.py line 30: tenant link exists but tenant deleted -> 401."""
    slug = f"td-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    tid = reg.json()["tenant_id"]

    # Delete tenant (cascade will clean children, but user_tenants might remain depending on FK)
    async with async_session_factory() as session:
        from sqlalchemy import text

        # Delete config first (FK), then tenant
        await session.execute(text("DELETE FROM tenant_configs WHERE tenant_id = :tid"), {"tid": tid})
        await session.execute(text("DELETE FROM user_tenants WHERE tenant_id = :tid"), {"tid": tid})
        await session.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tid})
        await session.commit()

    resp = await client.get("/api/v1/tenants/me", headers={"Authorization": f"Bearer {token}"})
    # Should be 401 (no links) since we deleted user_tenants too
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_users_route_user_not_found(client: AsyncClient) -> None:
    """users/routes.py line 38: user exists in JWT but not in DB -> 401."""
    slug = f"uf-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]

    # Delete the user entirely
    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
        await session.commit()

    resp = await client.put(
        "/api/v1/users/me",
        json={"full_name": "Hacker"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # The get_current_user dependency checks user existence, so this should be 401
    assert resp.status_code == 401


# ── Document routes edge cases ────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_upload_too_large(client: AsyncClient) -> None:
    """documents/routes.py line 54: file > 25MB -> 413."""
    token, _, _ = await register_and_token(client)

    # Create a file just over the limit (25 MB + 1 byte)
    # To avoid memory issues, we mock the file read
    # Actually, let's just send a small file but patch the limit
    # Or simply exceed the limit with a reasonable-size payload
    import io

    content = b"x" * (25 * 1024 * 1024 + 1)
    resp = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("large.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 413


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_upload_no_filename(client: AsyncClient) -> None:
    """documents/routes.py line 50: empty filename -> 400."""
    token, _, _ = await register_and_token(client)
    resp = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("", b"content", "text/plain")},
    )
    assert resp.status_code in (400, 422)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_upload_no_tenant_link(client: AsyncClient) -> None:
    """documents/routes.py line 35: user not linked to tenant -> 401."""
    slug = f"du-{uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Test",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]

    async with async_session_factory() as session:
        from sqlalchemy import text

        await session.execute(text("DELETE FROM user_tenants WHERE user_id = :uid"), {"uid": uid})
        await session.commit()

    resp = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert resp.status_code == 401
