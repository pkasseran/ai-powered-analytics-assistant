import logging
from typing import Dict, Optional, Any
from pathlib import Path
import yaml
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

from llm.openai_client import OpenAIChatClient
from utils.prompt_loader import build_system_prompt_from_yaml, get_llm_config_from_yaml
from config.settings import SETTINGS
from utils.agent_logging import parse_escaped_string

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".services.sql_generation")

# SAME USER PROMPT STYLE YOU HAD BEFORE
#- a time period column aligned to the requested the time grain {time_grain}, unless time grain is "none"
USER_PROMPT = """
SEMANTIC CONFIG (YAML):
{semantic_yaml}

REQUEST (Data Question):
Original Text: {original_text}
Metrics: {metrics}
Dimensions: {dimensions}
time_grain={time_grain}
time_range={time_range}
Filters: {filters}
Sort: {sort}
Top K: {top_k}

Output should include:
- all requested dimensions
- all requested metrics (aliased to their metric keys)
- sorted per the request
""".strip()

class SQLGenerationInput(BaseModel):
    semantic: Dict
    original_text: str
    metrics: list[str]
    dimensions: list[str]
    time_grain: Optional[str] = None
    time_range: Optional[str] = None
    filters: Optional[list[Any]] = None   # allow list[str] or list[dict]
    sort: Optional[str] = None
    top_k: Optional[int] = None
    previous_validation_error: Optional[str] = None

def _esc_braces(s: str) -> str:
    # Protect ChatPromptTemplate.format_messages from accidental `{` in YAML/text
    return s.replace("{", "{{").replace("}", "}}")

def _filters_to_str(filters: list[Any] | None) -> str:
    if not filters:
        return "[]"
    out = []
    for f in filters:
        if isinstance(f, str):
            out.append(f)
        elif isinstance(f, dict):
            field = f.get("field")
            op = f.get("op", "=")
            val = f.get("value")
            if isinstance(val, list):
                vals = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in val)
                val_str = f"({vals})"
            elif isinstance(val, str):
                val_str = f"'{val}'"
            else:
                val_str = str(val)
            out.append(f"{field} {op} {val_str}")
        else:
            out.append(str(f))
    return ", ".join(out)

class SQLGenerationService:
    def __init__(self, client: Optional[OpenAIChatClient] = None):
        # Load LLM config from YAML
        llm_cfg = get_llm_config_from_yaml(
            SETTINGS.CONFIG_YAML_PATH, "agent_data_extractor"
        )
        model = llm_cfg.get("model", SETTINGS.DEFAULT_LLM_MODEL)
        # You can also extract other config values if your client supports them
        temperature = llm_cfg.get("temperature", 0.0)
        max_retries = llm_cfg.get("max_retries", 3)

        self.client = client or OpenAIChatClient(model=model,
                                                 temperature=temperature,
                                                 max_retries=max_retries)

        self.system_prompt = build_system_prompt_from_yaml(
            SETTINGS.CONFIG_YAML_PATH, "agent_data_extractor"
        )
        # System comes from YAML; user prompt is your template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            ("user", USER_PROMPT),
        ])

    def generate_sql(self, payload: SQLGenerationInput) -> str:
        # Build the variables for ChatPromptTemplate
        semantic_yaml = yaml.safe_dump(payload.semantic, sort_keys=False)
        original_text = payload.original_text
        if payload.previous_validation_error:
            original_text += (
                f"\n\nPrevious SQL validation error: "
                f"{payload.previous_validation_error}\nPlease fix this."
            )

        # Fill messages using the SAME technique I had before using ChatPromptTemplate
        messages = self.prompt.format_messages(
            system_prompt=self.system_prompt,
            semantic_yaml=_esc_braces(semantic_yaml),
            original_text=_esc_braces(original_text),
            metrics=", ".join(payload.metrics),
            dimensions=", ".join(payload.dimensions),
            time_grain=payload.time_grain or "none",
            time_range=payload.time_range or "none",
            filters=_filters_to_str(payload.filters),
            sort=payload.sort or "none",
            top_k=payload.top_k or 0,
        )
        
        ###### Uncomment to debug prompts #####

        # log.info("System messages: %r",  self.system_prompt)
        # formatted_user_msg = parse_escaped_string(messages[1].content)
        # log.info("Formatted user message:\n%s", formatted_user_msg)
        
        # Optional: preview for debugging
        # try:
        #     preview = messages[1].content  # the user message
        #     log.info("User prompt preview:\n%s", preview[:800])
        # except Exception:
        #     pass

        resp = self.client.complete(messages)
        sql = resp.strip()
        log.info("LLM returned SQL (len=%d)", len(sql))
        return sql
