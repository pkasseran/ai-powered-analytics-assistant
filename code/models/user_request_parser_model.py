from __future__ import annotations
from typing import List, Literal, Optional, Union, Dict, Any
from pydantic import BaseModel, Field , root_validator
import pandas as pd

# ----- Core primitives -----
class TimeRange(BaseModel):
    start: Optional[str] = Field(None, description="ISO date or relative like 'last_month'")
    end: Optional[str] = Field(None, description="ISO date or relative like 'today'")

class Filter(BaseModel):
    field: str
    op: Literal["=", "!=", ">", "<", ">=", "<=", "in", "not_in", "between", "like"]
    value: Union[str, float, int, List[Union[str, float, int]]]

class ChartHint(BaseModel):
    encoding_rules: List[str] = Field(default_factory=list)
    
# ----- Work items -----
class DataQuestion(BaseModel):
    kind: Literal["data"] = "data"
    original_text: str
    metrics: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=list)
    # time_grain should be non-optional with a default value
    time_grain: Literal["daily", "weekly", "monthly", "quarterly", "yearly"] = "monthly"

    time_range: Literal["this_year", "last_year", "last_month", "past_30_days", 
                                 "past_90_days", "past_180_days", 
                                 "this_month", "current_month", "YTD", "MTD", "past_12_months", 
                                 "past_24_months", "past_36_months","past_3_years","past_2_years"] = "past_3_years"
    filters: List[Filter] = Field(default_factory=list)
    sort: Optional[str] = Field(default=None, description="e.g. '-revenue' for desc")
    top_k: Optional[int] = None
    template_id: Optional[str] = None
    dataset: Optional[str] = None #  will store json string that can be serialized 
    chart_hint: Optional[ChartHint] = None
    chart_figure_json: Optional[str] = None
    narrative: Optional[str] = None
    model_config = {
        "arbitrary_types_allowed": True
    }

# ----- Agent input/output state -----
class AgentInput(BaseModel):
    user_query: str

class AgentOutput(BaseModel):
    questions: List[DataQuestion]
    notes: Optional[str] = None
