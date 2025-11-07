from graphs.parser_graph import build_parser_graph
from states.agentic_orchestrator_state import AgenticOrchestratorState
from states.parser_state import UserRequestParserState
from config.settings import SETTINGS
# Optionally import logging
import logging
log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.run_parsing")

def run_parsing_node_old(state: AgenticOrchestratorState) -> AgenticOrchestratorState:
    # Prepare initial parser state from orchestrator state
    parser_state: UserRequestParserState = {
        "user_query": state.get("user_query", ""),
        # Optionally pass other fields if needed
    }
    parser_graph = build_parser_graph()
    parser_result = parser_graph.invoke(parser_state)
    # Merge parser_result directly into orchestrator state (inherits all fields)
    new_state: AgenticOrchestratorState = {**state, **parser_result, "progress_messages": state.get("progress_messages", []) + ["Parsing completed."]}
    log.info("run_parsing_node: is_valid=%s, validation_message=%s, progress_messages=%s", 
             new_state.get("is_valid"), 
             new_state.get("validation_message"), 
             new_state.get("progress_messages")
             )
    return {**state, **parser_result, "progress_messages": state.get("progress_messages", []) + ["Parsing completed."]}

def run_parsing_node(state: AgenticOrchestratorState) -> AgenticOrchestratorState:
    parser_state: UserRequestParserState = {
        "user_query": state.get("user_query", ""),
        # Optionally pass other fields if needed
    }
    parser_graph = build_parser_graph()
    parser_result = parser_graph.invoke(parser_state)
    # Only update progress_messages in the orchestrator state
    progress = state.get("progress_messages", [])
    progress.append("Parsing completed.")
    new_state: AgenticOrchestratorState = {**state, **parser_result, "progress_messages": progress}
    log.info("run_parsing_node: is_valid=%s, validation_message=%s, progress_messages=%s", 
             new_state.get("is_valid"), 
             new_state.get("validation_message"), 
             new_state.get("progress_messages")
             )
    return new_state
