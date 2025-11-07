# services/user_request_parsing_service.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Tuple, Optional

import yaml
from langchain_core.prompts import ChatPromptTemplate
from llm.openai_client import OpenAIChatClient
from utils.prompt_loader import get_llm_config_from_yaml

from config.settings import SETTINGS
from utils.prompt_loader import build_system_prompt_from_yaml, get_llm_config_from_yaml
from tools.user_parser_tools import alias_to_canonical, try_map_template

# Uses the same models you referenced
from models.user_request_parser_model import (
    AgentInput, AgentOutput, DataQuestion
)

log = logging.getLogger(SETTINGS.LOGGING_APP_NAME + ".services.parser")

USER_PROMPT = """\
{query}
""".strip()

ROOT_DIR = SETTINGS.ROOT_DIR
SYSTEM_PROMPT = build_system_prompt_from_yaml(ROOT_DIR / "config" / "config.yaml" , "agent_parser")


def _load_registry_and_templates() -> Tuple[dict, dict]:
    """
    Loads metrics registry (for alias mapping) and sql_templates mapping rules.
    Expect files at:
      ROOT_DIR/config/ag_user_query_parser_config/metrics.yaml
      ROOT_DIR/config/ag_user_query_parser_config/sql_templates.yaml
    """
    metrics_p = ROOT_DIR / "config" / "ag_user_query_parser_config" / "metrics.yaml"
    tmpls_p   = ROOT_DIR / "config" / "ag_user_query_parser_config" / "sql_templates.yaml"
    with metrics_p.open("r", encoding="utf-8") as f:
        reg = yaml.safe_load(f) or {}
    with tmpls_p.open("r", encoding="utf-8") as f:
        tmpls = yaml.safe_load(f) or {}
    return reg, tmpls


class UserRequestParsingService:
    """
    LLM-backed parser that converts free-text user queries into AgentOutput,
    then post-processes (i.e. canonicalization + template selection).
    """

    def __init__(
        self,
        client: Optional[OpenAIChatClient] = None,
        project_root: Path | None = None,
    ) -> None:
        # Load LLM config from YAML
        llm_cfg = get_llm_config_from_yaml(
            SETTINGS.CONFIG_YAML_PATH, "agent_parser"
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
            SETTINGS.CONFIG_YAML_PATH, "agent_parser"
        )
        
        log.info("Using system prompt:\n%s", self.system_prompt)

        # Resolve base dir: agentic_data_assistant root if not given
        self.base_dir = project_root or SETTINGS.ROOT_DIR
        self.registry, self.tmpl_rules = _load_registry_and_templates()

        user_prompt_with_metrics_and_dims = USER_PROMPT + "\n\nKnown metrics: " + ", ".join(self.registry.get("metrics", [])) + "\nKnown dimensions: " + ", ".join(self.registry.get("dimensions", []))

        # Compose the prompt once; system text passed via variable
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            ("user", user_prompt_with_metrics_and_dims),
        ])

    def _post_process(self, parsed: AgentOutput) -> AgentOutput:
        updated: List[DataQuestion] = []
        for q in parsed.questions:
            if isinstance(q, DataQuestion):
                # canonicalize metrics / dimensions
                q.metrics = [
                    alias_to_canonical.invoke({"word": m, "registry": self.registry})
                    for m in q.metrics
                ]
                q.dimensions = [
                    alias_to_canonical.invoke({"word": d, "registry": self.registry})
                    for d in q.dimensions
                ]

                primary_metric = q.metrics[0] if q.metrics else None
                group_cnt = len(q.dimensions)

                q.template_id = try_map_template.invoke({
                    "metric": primary_metric,
                    "time_grain": q.time_grain,
                    "group_by_cnt": group_cnt,
                    "tmpl_rules": self.tmpl_rules,
                })
                updated.append(q)
            else:
                updated.append(q)
        return AgentOutput(questions=updated, notes=parsed.notes)

    def parse(self, user_query: str) -> AgentOutput:
        """
        Keep this synchronous (to match your project style).
        """
        # Fill variables for ChatPromptTemplate
        variables = {
            "system_prompt": self.system_prompt,
            "query": user_query,
        }

        log.info("Parsing user query...")

        chain = self.prompt | self.client.llm.with_structured_output(AgentOutput)
        out: AgentOutput = chain.invoke(variables)
        print(out)
        log.info("Parser LLM returned - %d work items", len(out.questions))
        log.info("Parser LLM returned - %s", out.questions)

        post = self._post_process(out)
        log.info("Post-processed items: %d", len(post.questions))
        return post

    def parse_input(self, input_obj: AgentInput) -> AgentOutput:
        """Convenience wrapper if you want to pass the Pydantic AgentInput."""
        return self.parse(input_obj.user_query)
