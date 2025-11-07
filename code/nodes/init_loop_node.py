from typing import List
import logging
from states.agentic_orchestrator_state import AgenticOrchestratorState
from config.settings import SETTINGS

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.init_loop")

def init_loop_node(state: AgenticOrchestratorState) -> AgenticOrchestratorState:
    # ensure `questions` and `analysis_requests` are present in state['parsed']
    parsed = state["parsed"]
    dqs = [q for q in parsed.questions if q.__class__.__name__ == "DataQuestion"]
    ars = [q for q in parsed.questions if q.__class__.__name__ == "AnalysisRequest"]
    log.info("Init: %d DataQuestions, %d AnalysisRequests", len(dqs), len(ars))
    return {**state, "questions": dqs, "analysis_requests": ars, "current_idx": 0, "processed_questions": []}
