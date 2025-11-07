from typing import Dict, TypedDict, Optional, Any
import pandas as pd
from models.user_request_parser_model import DataQuestion

class DataExtractorState(TypedDict, total=False):
    semantic: Any
    data_question: DataQuestion
    sql: Optional[str]
    is_valid: Optional[bool]
    validation_error: Optional[dict]
    validation_attempts: Optional[int] # to track number of validation attempts
    df: Optional[pd.DataFrame]
    
