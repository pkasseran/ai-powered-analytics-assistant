import yaml
from typing import Any, Dict, List

def _yaml_block(data: Any) -> str:
    """Render a Python object as YAML with stable, readable formatting."""
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip()

def build_system_prompt_from_yaml(yaml_path: str, agent_name: str) -> str:
    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Look under data_assistant > agents
    agent_cfg: Dict[str, Any] = (
        cfg.get("data_assistant", {})
           .get("agents", {})
           .get(agent_name)
    )
    if not agent_cfg:
        raise ValueError(f"Agent '{agent_name}' not found in {yaml_path}")

    prompt_cfg: Dict[str, Any] = agent_cfg.get("prompt_config", {}) or {}

    lines: List[str] = [f"Agent: {agent_name}"]

    # Core prompt parts
    role = prompt_cfg.get("role")
    if role:
        lines.append(f"Role: {role}")

    context = prompt_cfg.get("context")
    if context:
        lines.append(f"Context: {context}")

    instruction = prompt_cfg.get("instruction")
    if instruction:
        lines.append("Instruction:")
        lines.append(instruction)

    # New: chart_hint_instruction (verbatim block the model must follow)
    chart_hint_instr = prompt_cfg.get("chart_hint_instruction")
    if chart_hint_instr:
        lines.append("**chart_hint_instruction**:")
        lines.append(chart_hint_instr)

    # New: few_shots (render cleanly so the LLM can pattern-match)
    few_shots = prompt_cfg.get("few_shots")
    if isinstance(few_shots, list) and few_shots:
        lines.append("Few-Shot Examples:")
        for i, ex in enumerate(few_shots, start=1):
            # Pull common fields if present; dump the rest to YAML
            user_query = ex.get("user_query")
            rest = {k: v for k, v in ex.items() if k != "user_query"}

            lines.append(f"Example {i}:")
            if user_query:
                lines.append("User Query:")
                lines.append(user_query)

            if rest:
                lines.append("Example Context & Expected Output (YAML):")
                lines.append(_yaml_block(rest))

    # Style / tone, goal, etc.
    style = prompt_cfg.get("style_or_tone")
    if isinstance(style, list) and style:
        lines.append("Style or Tone:")
        for s in style:
            lines.append(f"- {s}")

    goal = prompt_cfg.get("goal")
    if goal:
        lines.append(f"Goal: {goal}")

    return "\n".join(lines)

def get_llm_config_from_yaml(yaml_path: str, agent_name: str) -> Dict[str, Any]:
    """
    Extract the LLM configuration for a given agent from the YAML config file.
    llm_config:
        model: "gpt-4"
        temperature: 0.5
        max_retries: 1
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Look under data_assistant > agents
    agent_cfg: Dict[str, Any] = (
        cfg.get("data_assistant", {})
           .get("agents", {})
           .get(agent_name)
    )
    if not agent_cfg:
        raise ValueError(f"Agent '{agent_name}' not found in {yaml_path}")

    llm_cfg: Dict[str, Any] = agent_cfg.get("llm_config", {}) or {}
    return llm_cfg

##### TESTING #####
if __name__ == "__main__":
    # Usage
    import sys      
    import os
    # Add the parent directory to the Python path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from config.settings import SETTINGS
    ROOT_DIR = SETTINGS.ROOT_DIR
    system_prompt = build_system_prompt_from_yaml(
        f"{ROOT_DIR}/config/config.yaml",
        "agent_parser"  # or "agent_parser", etc.
    )
    print(system_prompt)

    # Get LLM config
    llm_cfg = get_llm_config_from_yaml(
        f"{ROOT_DIR}/config/config.yaml",
        "agent_parser"
    )
    print("\nLLM Config:", llm_cfg) 

    print(llm_cfg.get("model"))
