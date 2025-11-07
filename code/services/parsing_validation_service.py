import yaml
from typing import List, Tuple
from pathlib import Path
from models.user_request_parser_model import AgentOutput, DataQuestion
from config.settings import SETTINGS
import logging
log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".services.parsing_validation")

class ParsingValidationService:
    def __init__(self, metrics_yaml_path: str):
        with open(metrics_yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.metrics = set(cfg.get("metrics", []))
        self.dimensions = set(cfg.get("dimensions", []))
        self.aliases = cfg.get("aliases", {})

    def validate_agent_output(self, agent_output: AgentOutput) -> Tuple[bool, str]:
        """
        Validates AgentOutput against metrics.yaml.
        Returns (is_valid, message). If not valid, message is user-facing.
        """
        # Check for presence of DataQuestion
        has_data_question = any(isinstance(q, DataQuestion) for q in agent_output.questions)
        if not has_data_question:
            return False, "Sorry, I could not find any valid DataQuestion in your request. Please rephrase your query."

        # Check that each DataQuestion has at least one metric and one dimension
        missing_fields = []
        for idx, q in enumerate(agent_output.questions):
            if isinstance(q, DataQuestion):
                if not q.metrics or not q.dimensions:
                    missing = []
                    if not q.metrics:
                        missing.append("metric")
                    if not q.dimensions:
                        missing.append("dimension")
                    missing_fields.append((idx, missing, q.original_text))
        if missing_fields:
            messages = []
            for idx, fields, text in missing_fields:
                msg = (
                    f"I'm sorry, but I was unable to determine a valid {', '.join(fields)} from your request: '{text}'. "
                    "This means I could not identify a metric or dimension to analyze. "
                    "Please try rephrasing your question to specify what data or breakdown you are interested in."
                )
                messages.append(msg)
            return False, "\n".join(messages)

        invalid_items = []
        for idx, q in enumerate(agent_output.questions):
            if isinstance(q, DataQuestion):
                invalid_metrics = [m for m in q.metrics if m not in self.metrics]
                invalid_dims = [d for d in q.dimensions if d not in self.dimensions]
                if invalid_metrics or invalid_dims:
                    invalid_items.append((idx, invalid_metrics, invalid_dims, q.original_text))
        if invalid_items:
            messages = []
            for idx, metrics, dims, text in invalid_items:
                msg = f"Sorry, I cannot process your request: '{text}'. "
                if metrics:
                    msg += f"Unknown metrics: {', '.join(metrics)}. "
                if dims:
                    msg += f"Unknown dimensions: {', '.join(dims)}. "
                msg += "Please check your query and try again."
                messages.append(msg)
            return False, "\n".join(messages)
        return True, "Request is valid."
