from typing import Dict, Any, List
from metrics.aggregate_basic import extract_basic_metrics
from metrics.timing_breakdown import extract_timing_metrics


def _compute_baseline_per_test(baseline_runs: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    baseline_results: Dict[str, Dict[str, Any]] = {}
    for test_id, events in baseline_runs.items():
        basic = extract_basic_metrics(events)
        timing = extract_timing_metrics(events)
        merged: Dict[str, Any] = {}
        merged.update(basic)
        merged.update(timing)
        baseline_results[test_id] = merged
    return baseline_results


def compare_baselines(current_results: Dict[str, Dict[str, Any]], baseline_runs: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    baseline_metrics = _compute_baseline_per_test(baseline_runs)
    comparison: Dict[str, Dict[str, Any]] = {}
    for test_id, cur in current_results.items():
        base = baseline_metrics.get(test_id)
        if not base:
            continue
        entry: Dict[str, Any] = {}
        entry["baseline_status"] = base.get("status")
        entry["baseline_total_latency_sec"] = base.get("total_latency_sec")
        entry["baseline_parsing_latency_sec"] = base.get("parsing_latency_sec")
        entry["baseline_sql_generation_latency_sec"] = base.get("sql_generation_latency_sec")
        entry["baseline_sql_validation_latency_sec"] = base.get("sql_validation_latency_sec")
        entry["baseline_data_extract_latency_sec"] = base.get("data_extract_latency_sec")
        entry["baseline_chart_llm_latency_sec"] = base.get("chart_llm_latency_sec")
        entry["baseline_narrative_latency_sec"] = base.get("narrative_latency_sec")
        entry["baseline_sql_valid_logged"] = base.get("sql_valid_logged")
        entry["baseline_chart_valid_logged"] = base.get("chart_valid_logged")

        def delta(key):
            cur_val = cur.get(key)
            base_val = base.get(key)
            if isinstance(cur_val, (int, float)) and isinstance(base_val, (int, float)):
                return cur_val - base_val
            return None

        entry["delta_total_latency_sec"] = delta("total_latency_sec")
        entry["delta_parsing_latency_sec"] = delta("parsing_latency_sec")
        entry["delta_sql_generation_latency_sec"] = delta("sql_generation_latency_sec")
        entry["delta_sql_validation_latency_sec"] = delta("sql_validation_latency_sec")
        entry["delta_data_extract_latency_sec"] = delta("data_extract_latency_sec")
        entry["delta_chart_llm_latency_sec"] = delta("chart_llm_latency_sec")
        entry["delta_narrative_latency_sec"] = delta("narrative_latency_sec")
        comparison[test_id] = entry
    return comparison
