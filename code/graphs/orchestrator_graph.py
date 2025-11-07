from langgraph.graph import StateGraph, END
from states.agentic_orchestrator_state import AgenticOrchestratorState
from nodes.run_parsing_node import run_parsing_node
from nodes.init_loop_node import init_loop_node
from nodes.pick_next_question_node import pick_next_question_node
from nodes.run_extractor_node import run_extractor_node
from nodes.accumulate_and_advance_node import accumulate_and_advance_node
from nodes.run_render_chart_node import run_render_chart_node


def has_more(state):
    return "pick_next" if state["current_idx"] < len(state["questions"]) else "done"

def build_orchestrator_graph():
    g = StateGraph(AgenticOrchestratorState)
    g.add_node("run_parsing", run_parsing_node)
    g.add_node("init_loop", init_loop_node)
    g.add_node("pick_next", pick_next_question_node)
    g.add_node("run_extractor", run_extractor_node)
    g.add_node("accumulate", accumulate_and_advance_node)
    g.add_node("run_render_chart", run_render_chart_node)

    g.set_entry_point("run_parsing")
    # Conditional edge: if validation fails, end; else continue
    g.add_conditional_edges(
        "run_parsing",
        lambda state: "init_loop" if state.get("is_valid", False) else END,
        {"init_loop": "init_loop", END: END}
    )
    g.add_edge("init_loop", "pick_next")
    g.add_edge("pick_next", "run_extractor")
    g.add_edge("run_extractor", "run_render_chart")
    g.add_edge("run_render_chart", "accumulate")

    g.add_conditional_edges("accumulate", has_more, {"pick_next": "pick_next", "done": END})
    return g.compile()
