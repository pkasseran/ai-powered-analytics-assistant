"""
LangGraph workflow for agentic SQL extraction (StateGraph version):
- Node 1: LLM SQL generation
- Node 2: SQL validation
- Node 3: Data extraction
- Feedback loop: If SQL invalid, regenerate with error info
"""
from langgraph.graph import StateGraph, END

from nodes.sql_generate_node import make_sql_generate_node
from nodes.sql_validate_node import make_sql_validate_node
from nodes.sql_extract_node import make_sql_extract_node

from services.sql_generation_service import SQLGenerationService
from services.sql_validation_service import SQLValidationService
from services.data_extraction_service import DataExtractionService

from states.data_extractor_state import DataExtractorState


NODE_GENERATE_SQL = "generate_sql_node"
NODE_VALIDATE_SQL = "validate_sql_node"
NODE_EXTRACT_DATA = "extract_data_node"

def is_valid_old(state):
    return NODE_EXTRACT_DATA if state.get("is_valid", False) else NODE_GENERATE_SQL

def is_valid(state):
    if state.get("is_valid", False):
        return NODE_EXTRACT_DATA
    attempts = state.get("validation_attempts", 0)
    if attempts >= 3:
        return "done"
    # Increment attempts for next loop
    # state["validation_attempts"] = attempts + 1
    return NODE_GENERATE_SQL

def build_data_extractor_graph():
    # Instantiate infra once; inject into node factories
    gen = SQLGenerationService()
    validator = SQLValidationService()
    extractor = DataExtractionService()

    # Create concrete node callables
    generate_sql_node = make_sql_generate_node(gen)       # async node
    validate_sql_node = make_sql_validate_node(validator) # sync node
    extract_data_node = make_sql_extract_node(extractor)  # sync node

    # Build StateGraph using the shared agent state
    g = StateGraph(DataExtractorState)
    g.add_node(NODE_GENERATE_SQL, generate_sql_node)
    g.add_node(NODE_VALIDATE_SQL, validate_sql_node)
    g.add_node(NODE_EXTRACT_DATA, extract_data_node)

    g.set_entry_point(NODE_GENERATE_SQL)
    g.add_edge(NODE_GENERATE_SQL, NODE_VALIDATE_SQL)
    g.add_edge(NODE_EXTRACT_DATA, END)

    g.add_conditional_edges(NODE_VALIDATE_SQL, is_valid, {NODE_EXTRACT_DATA: NODE_EXTRACT_DATA, NODE_GENERATE_SQL: NODE_GENERATE_SQL, "done": END})
    
    # Feedback loop: valid → extract, else → regenerate
    # g.add_conditional_edges(
    #     NODE_VALIDATE_SQL,
    #     lambda state: NODE_EXTRACT_DATA if state.get("is_valid") else NODE_GENERATE_SQL
    # )

    return g.compile()
