from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field
import json

from .user_request_parser_model import DataQuestion, Filter, TimeRange

# ---------- Helpers ----------
def _fmt_value(v: Union[str, float, int]) -> str:
    """Quote strings safely; keep numbers as-is."""
    if isinstance(v, str):
        return json.dumps(v)
    return str(v)

def _format_filter(f: "Filter") -> str:
    """Format a Filter into a compact, SQL-like string for readability."""
    op_map = {
        "=": "=", "!=": "!=", ">": ">", "<": "<", ">=": ">=", "<=": "<=",
        "in": "IN", "not_in": "NOT IN", "between": "BETWEEN", "like": "LIKE",
    }
    op = op_map.get(f.op, f.op)

    if f.op in ("in", "not_in"):
        vals = f.value if isinstance(f.value, list) else [f.value]
        vals_str = ", ".join(_fmt_value(v) for v in vals)
        return f"{f.field} {op} ({vals_str})"

    if f.op == "between":
        if isinstance(f.value, list) and len(f.value) == 2:
            v1, v2 = f.value
            return f"{f.field} {op} {_fmt_value(v1)} AND {_fmt_value(v2)}"
        # graceful fallback
        last = f.value if not isinstance(f.value, list) else f.value[-1]
        return f"{f.field} = {_fmt_value(last)}"

    if f.op == "like":
        return f"{f.field} {op} {_fmt_value(f.value)}"

    return f"{f.field} {op} {_fmt_value(f.value)}"

# ---------- Target model as Pydantic BaseModel ----------
class DataQuestionInfo(BaseModel):
    kind: str
    original_text: str
    metrics: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=list)
    time_grain: str = "daily"                       # default if missing
    #time_range: Optional[Dict[str, Optional[str]]] = None
    time_range: Optional[str] = None
    filters: List[str] = Field(default_factory=list)
    sort: str = ""                                   # default if missing
    top_k: int = 0                                   # 0 == no limit
    template_id: Optional[str] = None

    @classmethod
    def from_dataquestion(cls, q: "DataQuestion") -> "DataQuestionInfo":
        if getattr(q, "kind", None) != "data":
            raise TypeError(f"Expected a DataQuestion (kind='data'), got kind={getattr(q, 'kind', None)!r}")

        filters_str = [_format_filter(f) for f in (q.filters or [])]
        time_grain = q.time_grain or "daily"
        sort = q.sort or (f"-{q.metrics[0]}" if q.metrics else "")
        top_k = q.top_k if q.top_k is not None else 0

        return cls(
            kind=q.kind,
            original_text=q.original_text,
            metrics=list(q.metrics or []),
            dimensions=list(q.dimensions or []),
            time_grain=time_grain,
            #time_range=_to_time_range_dict(q.time_range),
            time_range=q.time_range,
            filters=filters_str,
            sort=sort,
            top_k=top_k,
            template_id=q.template_id
        )

    @classmethod
    def from_many(cls, items: List["DataQuestion"]) -> List["DataQuestionInfo"]:
        return [cls.from_dataquestion(it) for it in items if getattr(it, "kind", None) == "data"]

# ---------- Example usage ----------
# info = DataQuestionInfo.from_dataquestion(your_dataquestion_instance)
# infos = DataQuestionInfo.from_many(list_of_mixed_items)
