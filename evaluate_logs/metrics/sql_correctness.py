from typing import Dict, Any, List
from datetime import datetime

from deepdiff import DeepDiff
from loaders.sqlalchemy_client import SQLAlchemyClient


def _extract_generated_sql(events: List[Dict[str, Any]]) -> str | None:
    """Extract the best SQL candidate from logs, preferring the last validated-OK SQL.

    Supported formats in messages:
    - "Running SQL: <sql>"
    - "Validating SQL (len=...):\n<sql>" followed by "SQL validation PASSED" or "Validation result: OK"
    The algorithm scans in order, tracks the most recent candidate SQL and
    records the last one that was explicitly validated as OK. If none validated,
    it falls back to the last candidate encountered.
    """
    last_candidate_sql: str | None = None
    last_ok_sql: str | None = None
    current_candidate_sql: str | None = None

    for e in events:
        msg = e.get("message", "") or ""
        if not msg:
            continue

        # New candidate from "Running SQL:" (may not have validation lines)
        if "Running SQL:" in msg:
            sql = msg.split("Running SQL:", 1)[1].strip()
            if sql:
                last_candidate_sql = sql
                current_candidate_sql = sql
            continue

        # New candidate from "Validating SQL (len=...):\n<sql>"
        if "Validating SQL" in msg and "):" in msg:
            idx = msg.find("):")
            if idx != -1:
                sql = msg[idx + 2 :].strip()
                if sql:
                    last_candidate_sql = sql
                    current_candidate_sql = sql
            continue

        # Mark current candidate as OK when we see a success line
        if ("SQL validation PASSED" in msg) or ("Validation result: OK" in msg):
            if current_candidate_sql:
                last_ok_sql = current_candidate_sql
            continue

    # Prefer the last OK SQL, else the last seen candidate
    return last_ok_sql or last_candidate_sql


def _normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normed = []
    for r in rows:
        out = {}
        for k, v in r.items():
            if isinstance(v, float):
                out[k] = round(v, 6)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            else:
                out[k] = v
        normed.append(out)
    return sorted(normed, key=lambda row: tuple(row.values()))


def evaluate_sql_correctness(events: List[Dict[str, Any]], gt_case: Dict[str, Any], db: SQLAlchemyClient) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "sql_correct": None,
        "sql_diff_summary": None,
        "sql_row_count_generated": None,
        "sql_row_count_ground_truth": None,
    }
    generated_sql = _extract_generated_sql(events)
    if not generated_sql:
        result["sql_diff_summary"] = "No generated SQL found in logs."
        return result

    reference_sql = gt_case.get("reference_sql")
    if not reference_sql:
        result["sql_diff_summary"] = "No reference_sql defined in ground_truth.yaml."
        return result

    try:
        gen_rows = db.run_sql(generated_sql)
        gt_rows = db.run_sql(reference_sql)
    except Exception as e:
        result["sql_diff_summary"] = f"SQL execution error: {e}"
        return result

    result["sql_row_count_generated"] = len(gen_rows)
    result["sql_row_count_ground_truth"] = len(gt_rows)

    gen_norm = _normalize_rows(gen_rows)
    gt_norm = _normalize_rows(gt_rows)

    diff = DeepDiff(gt_norm, gen_norm, significant_digits=6)
    if diff == {}:
        result["sql_correct"] = True
        result["sql_diff_summary"] = "No differences."
    else:
        result["sql_correct"] = False
        result["sql_diff_summary"] = str(diff)[:2000]
    return result
