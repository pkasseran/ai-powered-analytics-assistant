
# Evaluation assets

This folder contains inputs and outputs for the offline evaluator that scores end‑to‑end runs from structured JSONL logs. The evaluator is script‑relative (no dependence on your current working directory) and produces Markdown/HTML reports plus per‑test JSON artifacts.

## Files
- `ground_truth.yaml` — mapping from `test_id` (or `query_hash`) to case definitions: query text, reference SQL, and chart alignment fields.
- `output/` — generated reports (`report.md`, `report.html`, `failures.md`), summary plots, and per‑test JSON (`output/per_test/<test_id>.json`).

## Running the evaluator

Basic usage:
```bash
python evaluate_logs/run_eval.py path/to/your_logs.jsonl
```

With a baseline (second log file to diff high‑level metrics):
```bash
python evaluate_logs/run_eval.py path/to/new_logs.jsonl --baseline path/to/old_logs.jsonl
```

Environment requirements:
- `POSTGRES_URI` must point to the same database used during the runs (the evaluator executes `reference_sql` and generated SQL).
- If using a `.env` file, ensure it is loadable (run_eval.py calls `load_dotenv()`).

Output artifacts:
- `output/report.md` — overview metrics + per‑test table.
- `output/report.html` — HTML version (with optional charts if summary plotting succeeds).
- `output/failures.md` — aggregated samples of mismatches/diffs.
- `output/per_test/*.json` — normalized metrics per test_id.

## ground_truth.yaml schema

Minimal entry:
```yaml
your_test_id_here:
  query: "Human-readable query"
  description: "Optional description of the case"
  reference_sql: |
    -- SQL that produces the reference dataset
    SELECT ...
  expected_chart_type: line            # optional (documentation context)
  x_column: period                     # X-axis key for alignment
  series_dimension: product            # optional: categorical trace key; omit or set null for single-series charts
  expected_metric_columns:             # one or more metric columns (first used as y for comparison)
    - actual_revenue
```

Alignment logic:
- `x_column` and `series_dimension` (if present) form a composite key; the first of `expected_metric_columns` is treated as the y metric.
- If `series_dimension` is absent or not present in ground truth rows, a single‑series placeholder is used internally.

Reference SQL notes:
- `reference_sql` is required for SQL correctness and chart correctness vs ground truth. If it is intentionally blank, SQL and chart correctness will be reported as `None` for that test, but dataset‑based chart accuracy (see below) may still compute if the chart prompt included a dataset block.

## SQL selection algorithm
The evaluator prefers the **last SQL that passed validation**. It scans log messages for candidate SQL lines (e.g., `Running SQL:` or `Validating SQL (len=...)`) and marks the most recent one whose subsequent validation message indicates success (e.g., `SQL validation PASSED`). If no validated‑OK SQL is found, it falls back to the last candidate encountered.

## Chart extraction & correctness
Chart figure precedence:
1. Saved file at `logs/charts/<test_id>.json` (written by the runtime chart validation node).
2. A log line prefixed with `chart_full_json:` containing full figure JSON.
3. Fallback: the `Chart JSON preview (len=...)` message (may be truncated).

Ground‑truth chart correctness:
- Executes `reference_sql`, builds a map keyed by `(x_column, series_dimension|single_series)` and compares each chart point (`x`, `trace name`, `y`) within tolerance (1e-6). Reports:
  - `chart_correct` (boolean) — all points match
  - `chart_pct_points_correct`, mismatch counts, sample mismatches.

## Dataset-based chart accuracy
Independently of ground truth, the evaluator extracts the dataset embedded in the chart prompt (look for `Data Set:` fenced JSON). It compares rendered chart points to these dataset rows to ensure the chart faithfully visualizes what the agent supplied to the LLM. Metrics reported:
- `chart_points_match_dataset` (boolean)
- `chart_dataset_total_points`, `chart_dataset_mismatch_count`
- `chart_dataset_mismatches_sample`

## Token & cost usage
If runtime logs include `llm_usage` events with token counts (and optionally `cost_usd`), the evaluator aggregates:
- Total tokens, average tokens per test, and summed cost (if cost fields are present).
These appear in `report.md` under "Token & Cost Summary".

## Making ground truth picked up reliably
- The evaluator always reads `evaluate_logs/evaluation/ground_truth.yaml` relative to `run_eval.py` (no need to `cd`).
- Ensure log records carry `test_id` (or `query_hash`) matching ground truth keys.
- Start Postgres first; confirm `POSTGRES_URI` resolves and the reference SQL runs without interactive prompts.

## Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `sql_correct` is None | Missing `reference_sql` or test_id not in ground_truth.yaml | Add/verify entry; ensure keys match exactly |
| Chart metrics all None | No chart figure found (none of the three sources present) | Confirm `chart_full_json` emission or saved JSON file exists |
| `chart_dataset_*` fields None | Dataset block not logged | Ensure runtime includes `Data Set:` fenced JSON in chart prompt logs |
| Token summary blank | No `llm_usage` events emitted | Verify LLM client logs usage payloads |
| All SQL diffs | Validation passed on an early incorrect attempt | Confirm latest validated SQL is logged; retry run |

## Legacy behavior caveats
- Earlier versions only parsed truncated preview and lacked dataset‑based accuracy; upgrade ground_truth entries to include chart alignment fields for better reliability.
- If upgrading from old logs, missing `chart_full_json` lines may reduce accuracy; re-run with current chart validation node for full JSON emission.


