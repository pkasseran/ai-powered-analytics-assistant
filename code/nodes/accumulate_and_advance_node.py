import logging
from states.agentic_orchestrator_state import AgenticOrchestratorState
from config.settings import SETTINGS

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.accumulate")

def accumulate_and_advance_node(state: AgenticOrchestratorState) -> AgenticOrchestratorState:
    processed = list(state.get("processed_questions", []))
    processed.append(state["data_question"])
    next_idx = state["current_idx"] + 1
    log.info("Advance: processed=%d next_idx=%d", len(processed), next_idx)
    return {**state, "processed_questions": processed, "current_idx": next_idx}
