from langchain.tools import tool
from typing import Dict, Any
import plotly.graph_objects as go


def validate_plotly_fig_json_fn(fig_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a Plotly figure JSON using Plotly's built-in validation.

    Returns a structured result:
      {"valid": True} on success, or {"valid": False, "error": "..."} on failure.
    """
    try:
        fig = go.Figure(fig_json)
        # Ensure at least one trace exists
        if not fig.data:
            return {"valid": False, "error": "Plotly figure has no data traces."}
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@tool
def validate_plotly_fig_json(fig_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: Validate a Plotly figure JSON. Useful for agent-driven chart validation.

    Args:
        fig_json: A Plotly figure specification (dict) as produced by the charting agent.

    Returns:
        A dict of the form {"valid": bool, "error": Optional[str]}.
    """
    return validate_plotly_fig_json_fn(fig_json)
