from pathlib import Path
from typing import Dict, Any, List
import plotly.graph_objects as go


def generate_summary_plots(results: Dict[str, Dict[str, Any]], output_dir: Path) -> None:
    latencies: List[float] = [
        r.get("total_latency_sec")
        for r in results.values()
        if isinstance(r.get("total_latency_sec"), (int, float))
    ]
    if latencies:
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=latencies))
        fig_hist.update_layout(
            title="Total Latency Distribution (sec)",
            xaxis_title="Latency (sec)",
            yaxis_title="Count",
        )
        fig_hist.write_html(str(output_dir / "latency_hist.html"), include_plotlyjs="cdn")
