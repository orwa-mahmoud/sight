"""Edge case tests for Conversation + Message entities."""

from __future__ import annotations

from uuid import uuid4

from src.domain.conversations.entities import Conversation, Message
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole


def test_conversation_start_with_participant() -> None:
    participant = uuid4()
    c = Conversation.start(
        tenant_id=uuid4(),
        thread_id="t1",
        channel=ConversationChannel.WHATSAPP,
        participant_id=participant,
    )
    assert c.participant_id == participant
    assert c.channel == ConversationChannel.WHATSAPP


def test_message_create_with_tool_data() -> None:
    m = Message.create(
        conversation_id=uuid4(),
        tenant_id=uuid4(),
        role=ConversationRole.ASSISTANT,
        content="",
        tool_call_id="call_xyz",
        tool_args={"query": "test"},
        hidden=True,
    )
    assert m.tool_call_id == "call_xyz"
    assert m.tool_args == {"query": "test"}
    assert m.hidden is True


def test_message_create_with_tool_result() -> None:
    m = Message.create(
        conversation_id=uuid4(),
        tenant_id=uuid4(),
        role=ConversationRole.TOOL,
        content="3 results",
        tool_call_id="call_xyz",
        tool_result={"chunks": [1, 2, 3]},
    )
    assert m.tool_result == {"chunks": [1, 2, 3]}


def test_message_create_checkpoint() -> None:
    m = Message.create(
        conversation_id=uuid4(),
        tenant_id=uuid4(),
        role=ConversationRole.ASSISTANT,
        content="summary",
        is_checkpoint=True,
        token_count=100,
    )
    assert m.is_checkpoint is True
    assert m.token_count == 100


def test_message_create_with_request_id() -> None:
    m = Message.create(
        conversation_id=uuid4(),
        tenant_id=uuid4(),
        role=ConversationRole.USER,
        content="hi",
        request_id="abc123",
    )
    assert m.request_id == "abc123"
    assert len(m.pending_events) == 1
