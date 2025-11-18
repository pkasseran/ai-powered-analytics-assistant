import ast
import re
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

from loaders.sqlalchemy_client import SQLAlchemyClient


def _extract_chart_figure(events: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Attempt to extract a Plotly-like figure dict from log messages.

    Primary source: a line containing "Chart JSON preview (len=...):\n{...}".
    We handle extra trailing characters by slicing to the last closing brace.
    """
    # Option B: try to load from logs/charts/<test_id>.json if available
    test_id: Optional[str] = None
    for e in events:
        tid = e.get("test_id")
        if tid:
            test_id = tid
            break
    if test_id:
        # EVAL script runs from repo root; resolve base logs dir relative to repo root
        repo_root = Path(__file__).resolve().parents[2]  # .../evaluate_logs
        candidate = repo_root / "logs" / "charts" / f"{test_id}.json"
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as fh:
                    fig = json.load(fh)
                if isinstance(fig, dict):
                    return fig
            except Exception:
                pass

    for e in events:
        msg = e.get("message", "")
        if not msg:
            continue
        # Preferred: full JSON emission
        if msg.startswith("chart_full_json:"):
            raw = msg[len("chart_full_json:") :].strip()
            try:
                fig = json.loads(raw)
                if isinstance(fig, dict):
                    return fig
            except Exception:
                pass
        if "Chart JSON preview" in msg:
            # Try to extract the block from first '{' to the last '}'
            start = msg.find("{")
            end = msg.rfind("}")
            if start != -1 and end != -1 and end > start:
                block = msg[start : end + 1]
                # Quick sanity cleanup: strip leading/trailing whitespace
                block = block.strip()
                try:
                    fig = ast.literal_eval(block)
                    if isinstance(fig, dict):
                        return fig
                except Exception:
                    # Fallback: try to reduce repeated whitespace and attempt again
                    block2 = re.sub(r"\s+", " ", block)
                    try:
                        fig = ast.literal_eval(block2)
                        if isinstance(fig, dict):
                            return fig
                    except Exception:
                        continue
    return None


def _extract_dataset_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract the dataset JSON used for chart generation from log messages.

    Looks for a message containing 'Data Set:' followed by a fenced JSON block ```json ... ```.
    Returns a list of row dicts or empty list if not found/parsable.
    """
    for e in events:
        msg = e.get("message", "") or ""
        if "Data Set:" in msg and "```json" in msg:
            # capture between first ```json and next ```
            start = msg.find("```json")
            if start == -1:
                continue
            start += len("```json")
            end = msg.find("```", start)
            if end == -1:
                continue
            json_block = msg[start:end].strip()
            try:
                data = json.loads(json_block)
                if isinstance(data, list):
                    return [r for r in data if isinstance(r, dict)]
            except Exception:
                continue
    return []


def evaluate_chart_correctness(events: List[Dict[str, Any]], gt_case: Dict[str, Any], db: SQLAlchemyClient) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "chart_correct": None,
        "chart_pct_points_correct": None,
        "chart_mismatch_count": None,
        "chart_total_points": None,
        "chart_mismatches_sample": None,
        # dataset comparison metrics
        "chart_points_match_dataset": None,
        "chart_dataset_mismatch_count": None,
        "chart_dataset_total_points": None,
        "chart_dataset_mismatches_sample": None,
    }
    fig = _extract_chart_figure(events)
    if fig is None:
        result["chart_mismatches_sample"] = "No chart figure found in logs."
        return result

    reference_sql = gt_case.get("reference_sql")
    if not reference_sql:
        result["chart_mismatches_sample"] = "No reference_sql defined in ground_truth.yaml."
        return result

    x_key = gt_case.get("x_column", "period")
    series_dim = gt_case.get("series_dimension")  # may be None for single-series
    metric_columns = gt_case.get("expected_metric_columns") or ["actual_revenue"]
    y_key = metric_columns[0]

    try:
        gt_rows = db.run_sql(reference_sql)
    except Exception as e:
        result["chart_mismatches_sample"] = f"Ground-truth SQL execution error: {e}"
        return result

    # Detect whether ground-truth rows include a series dimension
    single_series = False
    if series_dim is None:
        single_series = True

    gt_map = {}
    for r in gt_rows:
        x_val = str(r.get(x_key))
        if single_series or (series_dim not in r):
            series_val = "__single_series__"
            single_series = True  # enforce single-series mode if series key is absent
        else:
            series_val = str(r.get(series_dim))
        metric_val = r.get(y_key, 0)
        try:
            metric_val = float(metric_val)
        except Exception:
            pass
        gt_map[(x_val, series_val)] = round(metric_val, 6)

    mismatches = []
    total_points = 0
    correct_points = 0

    for trace in fig.get("data", []):
        series_name = str(trace.get("name")) if not single_series else "__single_series__"
        xs = trace.get("x", [])
        ys = trace.get("y", [])
        for x, y in zip(xs, ys):
            total_points += 1
            key = (str(x), series_name)
            gt_val = gt_map.get(key)
            try:
                y_val = float(y)
            except Exception:
                y_val = y

            if gt_val is None:
                mismatches.append(f"({x}, {series_name}) missing in ground truth; chart={y_val}")
            else:
                if isinstance(y_val, (int, float)) and abs(gt_val - y_val) < 1e-6:
                    correct_points += 1
                else:
                    mismatches.append(f"({x}, {series_name}) gt={gt_val}, chart={y_val}")

    if total_points == 0:
        result["chart_mismatches_sample"] = "No points found in chart."
        result["chart_correct"] = None
        result["chart_pct_points_correct"] = None
        result["chart_mismatch_count"] = 0
        result["chart_total_points"] = 0
        return result

    pct = correct_points / total_points
    result["chart_correct"] = (pct == 1.0)
    result["chart_pct_points_correct"] = pct
    result["chart_mismatch_count"] = len(mismatches)
    result["chart_total_points"] = total_points
    result["chart_mismatches_sample"] = "\n".join(mismatches[:10]) if mismatches else "No mismatches."

    # Dataset vs chart alignment (independent of ground truth)
    dataset_rows = _extract_dataset_rows(events)
    if dataset_rows:
        ds_map = {}
        for r in dataset_rows:
            x_val = str(r.get(x_key))
            if single_series or (series_dim is None) or (series_dim not in r):
                series_val = "__single_series__"
            else:
                series_val = str(r.get(series_dim))
            metric_val = r.get(y_key, 0)
            try:
                metric_val = float(metric_val)
            except Exception:
                pass
            ds_map[(x_val, series_val)] = round(metric_val, 6)
        ds_total = 0
        ds_mismatches = []
        ds_correct = 0
        for trace in fig.get("data", []):
            series_name = (str(trace.get("name")) if not single_series else "__single_series__")
            xs = trace.get("x", [])
            ys = trace.get("y", [])
            for x, y in zip(xs, ys):
                ds_total += 1
                key = (str(x), series_name)
                ds_val = ds_map.get(key)
                try:
                    y_val = float(y)
                except Exception:
                    y_val = y
                if ds_val is None:
                    ds_mismatches.append(f"(dataset missing) ({x}, {series_name}) chart={y_val}")
                else:
                    if isinstance(y_val, (int, float)) and abs(ds_val - y_val) < 1e-6:
                        ds_correct += 1
                    else:
                        ds_mismatches.append(f"(value diff) ({x}, {series_name}) dataset={ds_val}, chart={y_val}")
        if ds_total > 0:
            ds_pct = ds_correct / ds_total
            result["chart_points_match_dataset"] = (ds_pct == 1.0)
            result["chart_dataset_mismatch_count"] = len(ds_mismatches)
            result["chart_dataset_total_points"] = ds_total
            result["chart_dataset_mismatches_sample"] = "\n".join(ds_mismatches[:10]) if ds_mismatches else "No mismatches."
        else:
            result["chart_points_match_dataset"] = None
            result["chart_dataset_mismatch_count"] = 0
            result["chart_dataset_total_points"] = 0
            result["chart_dataset_mismatches_sample"] = "No points in dataset extraction."
    else:
        result["chart_points_match_dataset"] = None
        result["chart_dataset_mismatch_count"] = None
        result["chart_dataset_total_points"] = None
        result["chart_dataset_mismatches_sample"] = "Dataset not found in logs."
    return result
