from pathlib import Path


def generate_html_report(results, output_path: Path) -> None:
    md_path = output_path.parent / "report.md"
    if not md_path.exists():
        html = "<html><body><h1>No Markdown report found</h1></body></html>"
        output_path.write_text(html, encoding="utf-8")
        return
    md_text = md_path.read_text(encoding="utf-8")
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8' />
  <title>Evaluation Report</title>
</head>
<body>
  <h1>Evaluation Report (Markdown View)</h1>
  <pre>{md_text}</pre>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
