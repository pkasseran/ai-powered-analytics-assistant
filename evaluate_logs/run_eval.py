import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from loaders.log_loader import load_runs
from loaders.ground_truth_loader import load_ground_truth
from loaders.sqlalchemy_client import SQLAlchemyClient
from metrics.aggregate_basic import extract_basic_metrics
from metrics.timing_breakdown import extract_timing_metrics
from metrics.sql_correctness import evaluate_sql_correctness
from metrics.chart_correctness import evaluate_chart_correctness
from metrics.narrative_ragas import evaluate_narrative_quality
from metrics.cost_usage import extract_cost_metrics
from metrics.baseline_compare import compare_baselines
from reports.report_markdown import generate_markdown_report
from reports.report_html import generate_html_report
from reports.report_failures import generate_failure_report
from reports.summary_charts import generate_summary_plots


# Make evaluation directory relative to this script's folder to avoid CWD issues
EVAL_DIR = (Path(__file__).resolve().parent / "evaluation").resolve()


def ensure_structure():
    folders = [
        EVAL_DIR,
        EVAL_DIR / "loaders",
        EVAL_DIR / "metrics",
        EVAL_DIR / "reports",
        EVAL_DIR / "utils",
        EVAL_DIR / "output",
        EVAL_DIR / "output/per_test",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

    gt_path = EVAL_DIR / "ground_truth.yaml"
    if not gt_path.exists():
        gt_path.write_text("# Add ground truth cases here\n", encoding="utf-8")


def evaluate(logfile: str, baseline_logfile: str | None = None):
    ensure_structure()
    runs = load_runs(logfile)
    ground_truth = load_ground_truth(EVAL_DIR / "ground_truth.yaml")
    db = SQLAlchemyClient()

    all_results: dict[str, dict] = {}
    per_test_dir = EVAL_DIR / "output" / "per_test"

    for test_id, events in runs.items():
        result: dict = {}
        basic = extract_basic_metrics(events)
        result.update(basic)

        timing = extract_timing_metrics(events)
        result.update(timing)

        gt_case = ground_truth.get(test_id)

        if gt_case:
            sql_eval = evaluate_sql_correctness(events, gt_case, db)
            result.update(sql_eval)
        else:
            result["sql_correct"] = None
            result["sql_diff_summary"] = "No ground truth found for this test_id."

        if gt_case:
            chart_eval = evaluate_chart_correctness(events, gt_case, db)
            result.update(chart_eval)
        else:
            result["chart_correct"] = None
            result["chart_pct_points_correct"] = None
            result["chart_mismatch_count"] = None
            result["chart_total_points"] = None
            result["chart_mismatches_sample"] = "No ground truth found for this test_id."

        narrative_metrics = evaluate_narrative_quality(events, gt_case, db) if gt_case else {
            "narrative_present": None,
            "narrative_length_chars": None,
            "narrative_coverage_score": None,
        }
        result.update(narrative_metrics)

        cost = extract_cost_metrics(events)
        result.update(cost)

        all_results[test_id] = result

        per_test_dir.mkdir(parents=True, exist_ok=True)
        with open(per_test_dir / f"{test_id}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    baseline_results = None
    if baseline_logfile:
        baseline_runs = load_runs(baseline_logfile)
        baseline_results = compare_baselines(all_results, baseline_runs)

    out_dir = EVAL_DIR / "output"
    report_md_path = out_dir / "report.md"
    generate_markdown_report(all_results, baseline_results, report_md_path)

    report_html_path = out_dir / "report.html"
    generate_html_report(all_results, report_html_path)

    failure_path = out_dir / "failures.md"
    generate_failure_report(all_results, failure_path)

    generate_summary_plots(all_results, out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile")
    parser.add_argument("--baseline", default=None)
    args = parser.parse_args()
    evaluate(args.logfile, args.baseline)
