
from langgraph.graph import StateGraph, END
from states.parser_state import UserRequestParserState
from nodes.parser_node import make_user_request_parser_node
from nodes.parser_validation_node import make_parser_validation_node
from services.parsing_service import UserRequestParsingService


def build_parser_graph():

    parser_service = UserRequestParsingService()
    parse_node = make_user_request_parser_node(parser_service)
    parser_validation_node = make_parser_validation_node()

    g = StateGraph(UserRequestParserState)
    g.add_node("parse", parse_node)
    g.add_node("parser_validation", parser_validation_node)

    g.set_entry_point("parse")
    g.add_edge("parse", "parser_validation")
    # End after validation
    g.add_edge("parser_validation", END)
    return g.compile()

if __name__ == "__main__":
    graph = build_parser_graph()
    initial = UserRequestParserState(user_query="Show me monthly revenue by product in 2024 and compare to budget.")
    final = graph.invoke(initial)
    print(final["parsed"])
