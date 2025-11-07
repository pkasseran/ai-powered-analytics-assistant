
from langgraph.graph import StateGraph, END
from states.charting_state import ChartingState
from nodes.chart_render_node import  make_render_chart_llm_node_no_validation
from nodes.chart_validate_node import make_chart_validate_node
from services.charting_service_llm import  ChartingServiceLLM

NODE_RENDER_CHARTS = "render_charts"
NODE_VALIDATE_CHARTS = "validate_charts"

def is_valid(state):
    if state.get("is_valid", False):
        return "done"
    attempts = state.get("validation_attempts", 0)
    if attempts >= 3:
        return "done"
    # Retry if not valid and attempts < 3
    return NODE_RENDER_CHARTS


def build_charting_graph():
    service = ChartingServiceLLM()
    render_llm_node = make_render_chart_llm_node_no_validation(service)
    validate_node = make_chart_validate_node(service)

    g = StateGraph(ChartingState)
    g.add_node(NODE_RENDER_CHARTS, render_llm_node)
    g.add_node(NODE_VALIDATE_CHARTS, validate_node)

    g.set_entry_point(NODE_RENDER_CHARTS)
    g.add_edge(NODE_RENDER_CHARTS, NODE_VALIDATE_CHARTS)

    # Conditional edge: if valid, end; if not, retry up to 3 times
    g.add_conditional_edges(
        NODE_VALIDATE_CHARTS,
        is_valid,
        {"done": END, NODE_RENDER_CHARTS: NODE_RENDER_CHARTS}
    )

    return g.compile()
