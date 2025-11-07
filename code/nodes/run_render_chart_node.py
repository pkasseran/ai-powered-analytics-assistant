import logging
from states.agentic_orchestrator_state import AgenticOrchestratorState
from graphs.charting_graph import build_charting_graph
from states.charting_state import ChartingState
import json

from config.settings import SETTINGS
log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.run_render_chart_for_question")

# build once at import; if you prefer, move inside the function
_CHARTING_APP = build_charting_graph()

def run_render_chart_node(state: AgenticOrchestratorState) -> AgenticOrchestratorState:
    dq = state["data_question"]
    charting_state: ChartingState = {"data_question": dq}
    out = _CHARTING_APP.invoke(charting_state)
    fig_json = out.get("plotly_fig_json")
    if isinstance(fig_json, dict) and fig_json is not None:
        fig_json = json.dumps(fig_json)
    is_valid = out.get("is_valid")
    narrative = out.get("narrative", "")
    if isinstance(narrative, dict):
        narrative = json.dumps(narrative)
    # attach fig_json back to the question
    try:
        dq.chart_figure_json = fig_json if is_valid else None  # type: ignore[attr-defined]
        dq.narrative = narrative  # type: ignore[attr-defined]
    except Exception:
        dq = dq.model_copy(update={"chart_figure_json": fig_json if is_valid else None})  # pydantic v2 fallback
        dq = dq.model_copy(update={"narrative": narrative})  # pydantic v2 fallback
    
    # Update progress messages
    progress = state.get("progress_messages", [])
    if is_valid:
        progress.append("Chart rendered successfully.")
    else:
        progress.append("Chart rendering failed.")
    log.info("Chart rendered. Valid: %s", is_valid)
    return {**state, "chart_figure_json": fig_json, 
            "data_question": dq, 
            "progress_messages": progress}
