
from __future__ import annotations
from typing import TypedDict
from langgraph.graph import StateGraph, END
from models.user_request_parser_model import AgentOutput, AgentInput

class UserRequestParserState(TypedDict):
    user_query: str
    parsed: AgentOutput
    is_valid: bool
    validation_message: str

