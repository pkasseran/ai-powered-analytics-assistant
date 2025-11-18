# Inside you’ll find:

- **run_eval.py** – main orchestrator:
    - Loads your JSON log file (with query_hash / test_id)
    - Loads ground_truth.yaml
    - Connects to Postgres via SQLAlchemy
    - Runs:
        - basic + timing metrics
        - SQL correctness vs ground truth
        - chart correctness vs ground truth dataset
        - simple narrative-coverage metric
        - token/cost aggregation
    - Writes:
        - evaluation/output/report.md
        - evaluation/output/report.html
        - evaluation/output/failures.md
        - evaluation/output/per_test/<test_id>.json
        - evaluation/output/latency_hist.html (Plotly)
    - loaders/
        - log_loader.py – groups events by test_id / query_hash
        - sqlalchemy_client.py – run_sql() using DATABASE_URL or PG_* env vars
        - ground_truth_loader.py – loads ground_truth.yaml
    - metrics/
        - aggregate_basic.py – status, dq_count, latency, flags like sql_valid_logged
        - timing_breakdown.py – parsing / SQL gen / validation / extract / chart / narrative timings
        - sql_correctness.py – executes generated vs reference SQL and DeepDiffs row sets
        - chart_correctness.py – compares Plotly traces to ground-truth dataset at (x, series)
        - narrative_ragas.py – simple coverage metric over key terms from ground-truth rows
        - cost_usage.py – sums tokens/costs if present in logs
        - baseline_compare.py – compares current run vs baseline logs (latency deltas, etc.)
    - reports/
        - report_markdown.py – overall summary + per-test table
        - report_html.py – wraps markdown in a simple HTML shell
        - report_failures.py – focuses on failing tests (status, SQL/Chart incorrect)
        - summary_charts.py – Plotly histogram for latency
- **ground_truth.yaml**
    - Template with comments showing how to define cases:
        - keyed by query_hash
        - reference_sql, x_column, series_dimension, expected_metric_columns, etc.


# How to use it

1. Unzip somewhere like:
~/projects/metaweave_evaluation/

2. Place your log file in that folder, e.g.:
ada_2025-11-17-104421_xxx.log

3. Edit evaluation/ground_truth.yaml to add entries like:
```yaml
299dcc77286a:
  query: "Show monthly revenue by product in 2025."
  reference_sql: |
    -- ground truth SQL here
    SELECT ...
  x_column: period
  series_dimension: product
  expected_metric_columns:
    - actual_revenue
```

4. From the evaluation parent folder, run:
```bash
cd evaluation_full
python run_eval.py /path/to/your_log.log
```
Optional baseline comparison:
```bash
python run_eval.py current_log.log --baseline baseline_log.log
```
That will populate evaluation/output/ with reports you can directly reference in your ReadyTensor publication as quantitative evaluation.

If you’d like, next we can:

- Add a concrete example ground_truth.yaml based on your sample query (Show monthly revenue by product in 2025.), or
- Tweak metric names/sections so they map 1:1 to the reviewer’s feedback wording (e.g. “Task success rate”, “SQL exact-match accuracy”, etc.).

