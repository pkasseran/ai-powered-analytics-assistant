# states/charting_state.py
from typing import TypedDict, List, Optional, Dict, Any
import pandas as pd
from models.user_request_parser_model import DataQuestion  # reuse your existing model

class ChartingState(TypedDict, total=False):
    data_question: DataQuestion
    is_valid: Optional[bool]
    validation_error: Optional[dict]
    validation_attempts: Optional[int]  # to track number of validation attempts
    #plotly_fig_json: Optional[Dict[str, Any]]
    plotly_fig_json: Optional[str]  # Store as JSON string
    narrative: Optional[str]
