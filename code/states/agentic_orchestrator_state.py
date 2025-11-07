from typing import Dict, TypedDict, Optional, List, Any
import pandas as pd

from states.parser_state import UserRequestParserState
from models.user_request_parser_model import DataQuestion

# ✔️ Inherit from the parser state (do NOT list TypedDict again)
class AgenticOrchestratorState(UserRequestParserState, total=False):
    # Shared inputs for extractor
    semantic: Any
    questions: List[DataQuestion]
    
    # Loop control
    current_idx: int
    processed_questions: List[DataQuestion]

    # Current work item + extractor output and charting output
    data_question: DataQuestion
    df: Optional[pd.DataFrame]
    # chart_figure_json: Optional[Dict[str, Any]]
    chart_figure_json: Optional[str]

    # Progress and status messages
    progress_messages: List[str] = ['Starting workflow...','Parsing user query...']