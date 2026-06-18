"""Contextual Retrieval (Anthropic) — situate each chunk in its document.

`LLMContextualizer` asks the tenant's LLM for a one-line context that places a
chunk within the whole document. That line is prepended to the chunk *before
embedding*, so the chunk's vector reflects what it's about in context — fixing
the classic "retrieved but missing the context to be useful" failure. Returns ""
on any failure, so the caller falls back to embedding the raw chunk (never worse).
"""

from __future__ import annotations

import structlog

from src.domain.llm.ports import LLMClientPort
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole

logger = structlog.get_logger()

_DOC_EXCERPT_CHARS = 8000
_CONTEXT_MAX_TOKENS = 80


class LLMContextualizer:
    """Generates a short context line for a chunk using the tenant's LLM."""

    def __init__(self, llm: LLMClientPort) -> None:
        self._llm = llm

    async def contextualize(self, *, document: str, chunk: str) -> str:
        messages = [
            LLMMessage(
                role=LLMMessageRole.SYSTEM,
                content=(
                    "You write a single short sentence that situates a chunk within its document "
                    "to improve search retrieval. Reply with ONLY that sentence — no preamble."
                ),
            ),
            LLMMessage(
                role=LLMMessageRole.USER,
                content=(
                    f"<document>\n{document[:_DOC_EXCERPT_CHARS]}\n</document>\n\n"
                    f"<chunk>\n{chunk}\n</chunk>\n\nShort context:"
                ),
            ),
        ]
        try:
            result = await self._llm.chat_with_tools(messages, max_tokens=_CONTEXT_MAX_TOKENS, temperature=0.0)
        except Exception:
            logger.warning("contextualizer.llm_failed", exc_info=True)
            return ""
        return result.text.strip()
