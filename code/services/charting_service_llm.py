import plotly.graph_objects as go
import logging
from typing import Dict, Optional, Any
import pandas as pd
from pathlib import Path
from pydantic import BaseModel
from utils.prompt_loader import build_system_prompt_from_yaml, get_llm_config_from_yaml
from tools.chart_validation_tools import validate_plotly_fig_json
from config.settings import SETTINGS
from llm.openai_client import OpenAIChatClient
from models.user_request_parser_model import DataQuestion, ChartHint

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".services.charting_llm")

USER_PROMPT = """
CHART HINT (JSON):
{chart_hint}

PREVIOUS RENDER CHART VALIDATION ERRORS:
{previous_validation_errors}
Please resolve any validation errors identified above when rendering the chart.

Data Set:
```json
{dq_dataset}
```
""".strip()

def chart_hint_to_dict(chart_hint: ChartHint) -> Dict[str, Any]:
    """
    Convert a ChartHint (Pydantic model) to a plain dictionary for LLM prompt consumption.
    Handles nested models and lists.
    """
    if hasattr(chart_hint, "model_dump"):
        return chart_hint.model_dump(by_alias=True, exclude_none=True)
    elif isinstance(chart_hint, dict):
        return chart_hint
    else:
        raise TypeError("Input must be a ChartHint or dict")

class ChartingServiceLLM:
    def __init__(self, client: Optional[OpenAIChatClient] = None):
        # Load LLM config from YAML
        llm_cfg = get_llm_config_from_yaml(
            SETTINGS.CONFIG_YAML_PATH, "agent_charting"
        )
        model = llm_cfg.get("model", SETTINGS.DEFAULT_LLM_MODEL)
        # Also extract other config values if your client supports them
        # When temperature is 0, the model will be more deterministic
        temperature = llm_cfg.get("temperature", 0.0)
        max_retries = llm_cfg.get("max_retries", 3)

        self.client = client or OpenAIChatClient(model=model, 
                                                 temperature=temperature, 
                                                 max_retries=max_retries)
        
        self.system_prompt = build_system_prompt_from_yaml(
            SETTINGS.CONFIG_YAML_PATH, "agent_charting"
        )
        self.user_prompt = USER_PROMPT

    def build_prompt(self, data_question: DataQuestion, previous_validation_errors: str= "None") -> str:
        chart_hint_dict = chart_hint_to_dict(data_question.chart_hint)
        
        dq_dataset = data_question.dataset if data_question.dataset else "[]"
        user_message = self.user_prompt.format(
            chart_hint=chart_hint_dict,
            previous_validation_errors=previous_validation_errors,
            dq_dataset=dq_dataset
        )
        return user_message

    def get_llm_client(self) -> OpenAIChatClient:
        return self.client

    def validate_chart(self, fig_json: Dict[str, Any]) -> bool:
        """
        Validate a Plotly figure JSON using the chart validation tool.
        Returns True if valid, raises ValueError if not.
        """
        result = validate_plotly_fig_json.invoke({"fig_json": fig_json})
        print("PK Validation result:", result)
        log.info("Chart validation tool result: %s", result)
        if result.get("valid"):
            return True
        else:
            error_msg = result.get("error", "Unknown validation error.")
            raise ValueError(f"Invalid Plotly figure JSON: {error_msg}")

    def generate_chart(self, data_question: DataQuestion, previous_validation_errors: str = "None") -> str:
        """
        Generate chart instructions or code from the LLM given a DataQuestion.
        """
        prompt = self.build_prompt(data_question, previous_validation_errors=previous_validation_errors)
        log.info("Built prompt for chart generation %s", prompt)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        log.info("Sending charting prompt to LLM (len=%d)", len(prompt))
        resp = self.client.complete(messages)
        log.info("LLM returned charting response (len=%d)", len(resp))
        return resp
    