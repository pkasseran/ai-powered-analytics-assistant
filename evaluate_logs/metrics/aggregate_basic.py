from datetime import datetime
from typing import List, Dict, Any


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", ""))


def extract_basic_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": None,
        "user_query": None,
        "dq_count": 0,
        "is_valid": None,
        "validation_message": None,
        "total_latency_sec": None,
        "chart_json_len": None,
        "narrative_len": None,
        "sql_valid_logged": None,
        "chart_valid_logged": None,
    }
    start_ts = None
    end_ts = None

    for e in events:
        event = e.get("event")
        msg = e.get("message", "")
        ts = parse_ts(e["timestamp"])

        if event == "run_started":
            start_ts = ts
            result["user_query"] = e.get("user_query")

        if event == "run_completed":
            end_ts = ts
            result["status"] = e.get("status")

        if "Parse node: produced" in msg:
            try:
                num = int(msg.split("produced")[1].split("work")[0].strip())
                result["dq_count"] = num
            except Exception:
                pass

        if event == "dq_chart_rendered":
            result["chart_json_len"] = e.get("chart_json_len")

        if event == "dq_narrative_rendered":
            result["narrative_len"] = e.get("narrative_len")

        if "SQL validation PASSED" in msg:
            result["sql_valid_logged"] = True
        if "SQL validation FAILED" in msg:
            result["sql_valid_logged"] = False

        if "Chart validation tool result" in msg:
            result["chart_valid_logged"] = "'valid': True" in msg

        if event == "run_state_summary":
            result["is_valid"] = e.get("is_valid")
            result["validation_message"] = e.get("validation_message")

    if start_ts and end_ts:
        result["total_latency_sec"] = (end_ts - start_ts).total_seconds()

    return result
