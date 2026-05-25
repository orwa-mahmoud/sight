"""Framework-agnostic tool type registry.

Maps tool names to their ToolDef definitions for the gateway to
resolve available tools dynamically per tenant configuration.
"""

from __future__ import annotations

from src.ai.tools.escalate_question import ESCALATE_QUESTION_DEF
from src.ai.tools.remove_key_fact import REMOVE_KEY_FACT_DEF
from src.ai.tools.save_key_fact import SAVE_KEY_FACT_DEF
from src.ai.tools.search_documents import SEARCH_DOCUMENTS_DEF
from src.ai.types import ToolDef

ALL_TOOLS: dict[str, ToolDef] = {
    SEARCH_DOCUMENTS_DEF.name: SEARCH_DOCUMENTS_DEF,
    ESCALATE_QUESTION_DEF.name: ESCALATE_QUESTION_DEF,
    SAVE_KEY_FACT_DEF.name: SAVE_KEY_FACT_DEF,
    REMOVE_KEY_FACT_DEF.name: REMOVE_KEY_FACT_DEF,
}

ASKER_TOOLS = [SEARCH_DOCUMENTS_DEF, ESCALATE_QUESTION_DEF, SAVE_KEY_FACT_DEF, REMOVE_KEY_FACT_DEF]
OWNER_TOOLS = [SEARCH_DOCUMENTS_DEF]  # owner chat: search only, no escalation
