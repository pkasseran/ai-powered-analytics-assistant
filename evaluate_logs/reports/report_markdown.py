from pathlib import Path
import statistics
from typing import Dict, Any, Optional


def _safe_list(values):
    return [v for v in values if isinstance(v, (int, float))]


def _pct(n, d):
    return f"{(n / d * 100):.1f}%" if d and n is not None else "n/a"


def generate_markdown_report(results: Dict[str, Dict[str, Any]], baseline_results: Optional[Dict[str, Dict[str, Any]]], output_path: Path) -> None:
    lines = []
    lines.append("# Multi-Agent Analytics Assistant — Evaluation Report\n")
    test_ids = list(results.keys())
    total = len(test_ids)

    statuses = [results[t].get("status") for t in test_ids]
    ok_count = sum(1 for s in statuses if s == "ok")

    sql_correct_vals = [results[t].get("sql_correct") for t in test_ids]
    sql_correct_true = sum(1 for v in sql_correct_vals if v is True)

    chart_correct_vals = [results[t].get("chart_correct") for t in test_ids]
    chart_correct_true = sum(1 for v in chart_correct_vals if v is True)

    # Dataset-based chart accuracy (Option B metrics)
    ds_total_points = 0
    ds_correct_points = 0
    for t in test_ids:
        total_pts = results[t].get("chart_dataset_total_points")
        mismatch_cnt = results[t].get("chart_dataset_mismatch_count")
        # Only count if numbers are present
        if isinstance(total_pts, int) and isinstance(mismatch_cnt, int) and total_pts > 0:
            ds_total_points += total_pts
            ds_correct_points += (total_pts - mismatch_cnt)
    chart_accuracy_pct = (ds_correct_points / ds_total_points * 100) if ds_total_points else None

    total_latencies = _safe_list(results[t].get("total_latency_sec") for t in test_ids)
    avg_latency = statistics.mean(total_latencies) if total_latencies else None
    p50_latency = statistics.median(total_latencies) if total_latencies else None

    lines.append("## Overview\n")
    lines.append(f"- **Total test cases:** {total}")
    lines.append(f"- **Successful runs (status='ok'):** {ok_count} ({_pct(ok_count, total)})")
    lines.append(f"- **SQL correctness (vs ground truth):** {sql_correct_true} / {total} ({_pct(sql_correct_true, total)})")
    lines.append(f"- **Chart correctness (vs ground truth):** {chart_correct_true} / {total} ({_pct(chart_correct_true, total)})")
    if chart_accuracy_pct is not None:
        lines.append(f"- **Chart accuracy (dataset points match):** {chart_accuracy_pct:.1f}% ({ds_correct_points}/{ds_total_points} points)")
    else:
        lines.append("- **Chart accuracy (dataset points match):** n/a (no parsed chart points)")
    if avg_latency is not None:
        lines.append(f"- **Average total latency:** {avg_latency:.2f} sec")
    if p50_latency is not None:
        lines.append(f"- **p50 latency:** {p50_latency:.2f} sec")
    lines.append("")

    # Metrics methodology section
    lines.append("## How metrics are calculated\n")
    lines.append("(All metrics are derived solely from structured log events; script names below refer to logic but the authoritative source is the log content.)")
    lines.append("- Total test cases: Count of distinct test_id values appearing in any log record.")
    lines.append("- Successful runs (status='ok'): Determined from a `run_completed` log event with `status='ok'` for each test_id.")
    lines.append("- SQL correctness (vs ground truth):")
    lines.append("  - Log sources: 'Validating SQL ...' messages, 'SQL validation PASSED' / 'Validation result: OK', and any preceding candidate SQL messages; reference_sql loaded via ground_truth.yaml.")
    lines.append("  - Method: Take the last SQL that passed validation, execute both it and reference_sql, normalize rows (round floats, ISO8601 datetimes), diff with DeepDiff; correct when diff is empty.")
    lines.append("- Chart correctness (vs ground truth):")
    lines.append("  - Log sources: 'chart_full_json' emission or 'Chart JSON preview', plus reference_sql output rows.")
    lines.append("  - Method: Parse chart JSON traces; execute reference_sql; build ground-truth map keyed by (x_column, series_dimension or single-series placeholder) and compare each (x, series, y) with tolerance 1e-6.")
    lines.append("- Chart accuracy (dataset points match):")
    lines.append("  - Log sources: The 'Data Set:' fenced JSON block in the chart prompt and the chart JSON ('chart_full_json' or preview).")
    lines.append("  - Method: Build dataset map keyed by (x, series or placeholder) and measure matched vs total chart points (exact float match within tolerance).")
    lines.append("- Latency metrics: Derived from timestamps of lifecycle events (e.g., run_started to run_completed); p50 is the median of per-test total latencies.")
    lines.append("- Token & Cost Summary:")
    lines.append("  - Log sources: 'llm_usage' structured events with prompt_tokens, completion_tokens, total_tokens, model; cost_usd if present is summed directly.")
    lines.append("  - Method: Aggregate tokens per test_id; totals/averages reported; cost is a direct sum of logged cost_usd fields (if any).")
    lines.append("")

    total_tokens = _safe_list(results[t].get("total_tokens") for t in test_ids)
    total_costs = _safe_list(results[t].get("total_cost_usd") for t in test_ids)
    if total_tokens:
        lines.append("## Token & Cost Summary\n")
        lines.append(f"- **Total tokens (all tests):** {int(sum(total_tokens))}")
        lines.append(f"- **Average tokens per test:** {statistics.mean(total_tokens):.1f}")
        if total_costs:
            lines.append(f"- **Total cost (USD):** ${sum(total_costs):.4f}")
        lines.append("")

    lines.append("## Per-Test Metrics\n")
    lines.append("| Test ID | Status | SQL Correct | Chart Correct | Dataset Points | Dataset Mismatches | Chart Accuracy % | Total Latency (sec) |")
    lines.append("|---------|--------|-------------|---------------|---------------|--------------------|------------------|---------------------|")

    for tid in test_ids:
        r = results[tid]
        total_pts = r.get("chart_dataset_total_points")
        mismatch_cnt = r.get("chart_dataset_mismatch_count")
        if isinstance(total_pts, int) and isinstance(mismatch_cnt, int) and total_pts > 0:
            acc_pct = (total_pts - mismatch_cnt) / total_pts * 100
            acc_str = f"{acc_pct:.1f}%"
        else:
            acc_str = "n/a"
        lines.append(
            "| `{tid}` | {status} | {sql_corr} | {chart_corr} | {pts} | {mm} | {acc} | {tot_lat} |".format(
                tid=tid,
                status=r.get("status", "n/a"),
                sql_corr=r.get("sql_correct"),
                chart_corr=r.get("chart_correct"),
                pts=total_pts if isinstance(total_pts, int) else "n/a",
                mm=mismatch_cnt if isinstance(mismatch_cnt, int) else "n/a",
                acc=acc_str,
                tot_lat=f"{r.get('total_latency_sec'):.2f}" if isinstance(r.get("total_latency_sec"), (int, float)) else "n/a",
            )
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")
