from datetime import datetime
from typing import List, Dict, Any


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", ""))


def _first_ts(events, predicate):
    for e in events:
        if predicate(e):
            return parse_ts(e["timestamp"])
    return None


def _delta(start, end):
    if start and end:
        return (end - start).total_seconds()
    return None


def extract_timing_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    parsing_start = _first_ts(events, lambda e: "Parsing user query" in e.get("message", ""))
    parsing_end = _first_ts(events, lambda e: e.get("event") == "progress" and e.get("message") == "Parsing completed.")

    sql_gen_start = _first_ts(events, lambda e: e.get("event") == "progress" and e.get("message", "").startswith("Extracting data for question"))
    sql_gen_end = _first_ts(events, lambda e: "LLM returned SQL" in e.get("message", ""))

    sql_val_start = _first_ts(events, lambda e: "Validating SQL" in e.get("message", ""))
    sql_val_end = _first_ts(events, lambda e: "SQL validation PASSED" in e.get("message", "") or "SQL validation FAILED" in e.get("message", ""))

    data_start = _first_ts(events, lambda e: "Executing SQL and loading DataFrame" in e.get("message", ""))
    data_end = _first_ts(events, lambda e: "Extracted df shape" in e.get("message", ""))

    chart_llm_start = _first_ts(events, lambda e: "Sending charting prompt to LLM" in e.get("message", ""))
    chart_llm_end = _first_ts(events, lambda e: "LLM returned charting response" in e.get("message", ""))

    narrative_start = _first_ts(events, lambda e: "Chart rendered. Valid" in e.get("message", ""))
    narrative_end = _first_ts(events, lambda e: e.get("event") == "dq_narrative_rendered")

    return {
        "parsing_latency_sec": _delta(parsing_start, parsing_end),
        "sql_generation_latency_sec": _delta(sql_gen_start, sql_gen_end),
        "sql_validation_latency_sec": _delta(sql_val_start, sql_val_end),
        "data_extract_latency_sec": _delta(data_start, data_end),
        "chart_llm_latency_sec": _delta(chart_llm_start, chart_llm_end),
        "narrative_latency_sec": _delta(narrative_start, narrative_end),
    }
