# nodes/user_request_parser_node.py
import logging
from typing import TypedDict, Optional

from services.parsing_service import UserRequestParsingService
from states.parser_state import UserRequestParserState
from config.settings import SETTINGS
log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.user_request_parser")

def make_user_request_parser_node(parser: UserRequestParsingService):
    """
    Thin node wrapper: reads `user_query` from state, writes `parsed` (AgentOutput).
    """
    def node(state: UserRequestParserState) -> UserRequestParserState:
        uq = state.get("user_query") or ""
        log.info("Parse node: received user_query (len=%d)", len(uq))
        parsed = parser.parse(uq)
        log.info("Parse node: produced %d work items", len(parsed.questions))
        return {**state, "parsed": parsed}
    return node
