"""Direct use case tests — bypass HTTP to cover use case bodies precisely."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.auth.commands import AuthenticateUser, RegisterOwner
from src.application.auth.use_cases.authenticate_user import AuthenticateUserUseCase
from src.application.auth.use_cases.get_user_by_id import GetUserByIdUseCase
from src.application.auth.use_cases.register_owner import RegisterOwnerUseCase
from src.application.questions.commands import CloseQuestion, ReplyToQuestion, SubmitQuestion
from src.application.questions.queries import GetQuestion, ListQuestions
from src.application.questions.use_cases.close_question import CloseQuestionUseCase
from src.application.questions.use_cases.list_questions import GetQuestionUseCase, ListQuestionsUseCase
from src.application.questions.use_cases.reply_to_question import ReplyToQuestionUseCase
from src.application.questions.use_cases.submit_question import SubmitQuestionUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.shared.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    EntityNotFoundError,
    InvalidOperationError,
)
from src.infrastructure.auth.bcrypt_hasher import BcryptPasswordHasher
from src.infrastructure.auth.jwt_service import JwtService
from src.infrastructure.persistence.postgres.database import async_session_factory

_HASHER = BcryptPasswordHasher(rounds=4)
_JWT = JwtService(secret_key="test-secret")


async def _register(uow: UnitOfWork, slug: str | None = None) -> tuple:  # type: ignore[type-arg]
    slug = slug or f"s-{uuid4().hex[:8]}"
    uc = RegisterOwnerUseCase(uow=uow, password_hasher=_HASHER, jwt_service=_JWT)
    result = await uc.execute(
        RegisterOwner(
            email=f"{slug}@test.com",
            password="longpassword123",
            full_name="Test",
            tenant_name=f"Tenant {slug}",
            tenant_slug=slug,
        )
    )
    return result.user_id, result.tenant_id, result.access_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_validates_short_password(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = RegisterOwnerUseCase(uow=uow, password_hasher=_HASHER, jwt_service=_JWT)
        with pytest.raises(InvalidOperationError, match="Password"):
            await uc.execute(
                RegisterOwner(email="x@y.com", password="short", full_name=None, tenant_name="T", tenant_slug="ts")
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_validates_bad_slug(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = RegisterOwnerUseCase(uow=uow, password_hasher=_HASHER, jwt_service=_JWT)
        with pytest.raises(InvalidOperationError, match="slug"):
            await uc.execute(
                RegisterOwner(
                    email="a@b.com", password="longpassword", full_name=None, tenant_name="T", tenant_slug="INVALID!"
                )
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_rejects_duplicate_email_via_use_case(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await _register(uow, slug="dup-email")
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = RegisterOwnerUseCase(uow=uow, password_hasher=_HASHER, jwt_service=_JWT)
        with pytest.raises(AlreadyExistsError, match="email"):
            await uc.execute(
                RegisterOwner(
                    email="dup-email@test.com",
                    password="longpassword",
                    full_name=None,
                    tenant_name="X",
                    tenant_slug="dup-email-2",
                )
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authenticate_user_success(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await _register(uow, slug="auth-ok")
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = AuthenticateUserUseCase(uow=uow, password_hasher=_HASHER, jwt_service=_JWT)
        result = await uc.execute(AuthenticateUser(email="auth-ok@test.com", password="longpassword123"))
        assert result.access_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await _register(uow, slug="auth-bad")
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = AuthenticateUserUseCase(uow=uow, password_hasher=_HASHER, jwt_service=_JWT)
        with pytest.raises(AuthenticationError):
            await uc.execute(AuthenticateUser(email="auth-bad@test.com", password="wrong"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authenticate_user_nonexistent_email(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = AuthenticateUserUseCase(uow=uow, password_hasher=_HASHER, jwt_service=_JWT)
        with pytest.raises(AuthenticationError):
            await uc.execute(AuthenticateUser(email="nope@nope.com", password="anything"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_user_by_id_success(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        user_id, _, _ = await _register(uow, slug="getme")
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        dto = await GetUserByIdUseCase(uow=uow).execute(user_id)
        assert dto.email == "getme@test.com"
        assert dto.role == "owner"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_user_by_id_not_found(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        with pytest.raises(EntityNotFoundError):
            await GetUserByIdUseCase(uow=uow).execute(uuid4())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_question_reply_and_close_via_use_case(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        user_id, tenant_id, _ = await _register(uow, slug="q-uc")
        await uow.commit()
    # Submit
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        q_dto = await SubmitQuestionUseCase(uow=uow).execute(
            SubmitQuestion(tenant_id=tenant_id, channel=ConversationChannel.WEB, question_text="Test Q")
        )
        await uow.commit()
    # Reply (use the actual user_id — FK enforced)
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        replied = await ReplyToQuestionUseCase(uow=uow).execute(
            ReplyToQuestion(tenant_id=tenant_id, question_id=q_dto.id, replied_by_user_id=user_id, reply="Done!")
        )
        assert replied.status == "resolved"
        await uow.commit()
    # Submit another then close
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        q2 = await SubmitQuestionUseCase(uow=uow).execute(
            SubmitQuestion(tenant_id=tenant_id, channel=ConversationChannel.TELEGRAM, question_text="Close me")
        )
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        closed = await CloseQuestionUseCase(uow=uow).execute(CloseQuestion(tenant_id=tenant_id, question_id=q2.id))
        assert closed.status == "closed"
        await uow.commit()
    # List + Get
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        all_q = await ListQuestionsUseCase(uow=uow).execute(ListQuestions(tenant_id=tenant_id))
        assert len(all_q) == 2
        single = await GetQuestionUseCase(uow=uow).execute(GetQuestion(tenant_id=tenant_id, question_id=q_dto.id))
        assert single.status == "resolved"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_question_cross_tenant_blocked(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        _, tid_a, _ = await _register(uow, slug="xta")
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        _, tid_b, _ = await _register(uow, slug="xtb")
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        q = await SubmitQuestionUseCase(uow=uow).execute(
            SubmitQuestion(tenant_id=tid_a, channel=ConversationChannel.WEB, question_text="From A")
        )
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        with pytest.raises(AuthorizationError):
            await GetQuestionUseCase(uow=uow).execute(GetQuestion(tenant_id=tid_b, question_id=q.id))
