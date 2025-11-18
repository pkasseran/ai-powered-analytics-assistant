from pathlib import Path
from typing import Dict, Any


def generate_failure_report(results: Dict[str, Dict[str, Any]], output_path: Path) -> None:
    lines = []
    lines.append("# Failure Report\n")
    failures = []
    for tid, r in results.items():
        status = r.get("status")
        sql_correct = r.get("sql_correct")
        chart_correct = r.get("chart_correct")
        if status != "ok" or sql_correct is False or chart_correct is False:
            failures.append((tid, r))

    if not failures:
        lines.append("No failures detected.")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.append(f"Total failing tests: **{len(failures)}**\n")
    for tid, r in failures:
        lines.append(f"## Test `{tid}`")
        lines.append(f"- Query: `{r.get('user_query', '')}`")
        lines.append(f"- Status: {r.get('status')}")
        lines.append(f"- SQL Correct: {r.get('sql_correct')}")
        lines.append(f"- SQL Diff: {str(r.get('sql_diff_summary', ''))[:500]}")
        lines.append(f"- Chart Correct: {r.get('chart_correct')}")
        lines.append(f"- Chart Mismatches: {r.get('chart_mismatches_sample', '')}")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
