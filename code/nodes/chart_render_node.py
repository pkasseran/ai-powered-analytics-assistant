# nodes/render_charts_node.py
import logging
from typing import List, Dict, Any
from states.charting_state import ChartingState
from services.charting_service_llm import ChartingServiceLLM
from config.settings import SETTINGS

import json

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".nodes.render_chart")

def make_render_chart_llm_node_no_validation(service_llm: ChartingServiceLLM):
    """
    Reads state['data_question'] (single DataQuestion) and writes state['figure_llm'] (single fig_json) using ChartingServiceLLM.
    Does NOT validate the generated figure JSON (validation should be done in a separate node).
    """
    def node(state: ChartingState) -> ChartingState:
        dq = state.get("data_question", None)
        if dq is None:
            log.warning("No DataQuestion found in state.")
            plotly_fig_json = None
        else:
            log.info("Rendering chart with LLM for DataQuestion: %s", getattr(dq, "original_text", ""))
            previous_validation_errors = state.get("validation_error", "None")
            resp = service_llm.generate_chart(dq, previous_validation_errors=previous_validation_errors)
            #print(f"LLM Chart response: {resp}")
            # resp is str (JSON string) with 2 keys 
            # {
            #    "plotly_figure": <the EXACT Plotly figure JSON>,
            #    "narrative": "<plain-text analysis>"
            #    }
            # Extract the plotly_figure and narrative
            try:
                resp_dict = json.loads(resp)
                plotly_fig_json = resp_dict.get("plotly_figure", None)
                narrative = resp_dict.get("narrative", "")
            except json.JSONDecodeError as e:
                log.error(f"Failed to decode JSON response from LLM: {e}")
                plotly_fig_json = None
        
        return {**state, "plotly_fig_json": plotly_fig_json, "narrative": narrative}
    return node


