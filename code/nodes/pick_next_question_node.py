import logging
from states.agentic_orchestrator_state import AgenticOrchestratorState
from config.settings import SETTINGS
log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.pick_next")

def pick_next_question_node(state: AgenticOrchestratorState) -> AgenticOrchestratorState:
    i = state["current_idx"]
    dq = state["questions"][i]
    progress = state.get("progress_messages", [])
    progress.append(f"Processing question {i+1} of {len(state['questions'])}.")
    progress.append(f"Extracting data for question {i+1} of {len(state['questions'])}.")
    # Add detailed logging for the picked question
    log.info("Pick DQ #%d: metrics=%s dims=%s", i, getattr(dq, "metrics", None), getattr(dq, "dimensions", None))
    return {**state, "data_question": dq, "progress_messages": progress}
