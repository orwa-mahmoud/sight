"""Conversation queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class LoadThreadHistory:
    thread_id: str
    limit: int | None = None
    include_hidden: bool = True
    # Load only from the most recent checkpoint onward (the checkpoint summary
    # stands in for everything before it). Bounds the agent's context so a long
    # conversation doesn't resend its full history every turn.
    from_last_checkpoint: bool = False
