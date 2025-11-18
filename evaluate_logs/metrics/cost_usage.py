from typing import Dict, Any, List


def extract_cost_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    total_cost = 0.0
    models = set()
    any_token_info = False
    any_cost_info = False

    for e in events:
        prompt_t = e.get("prompt_tokens")
        compl_t = e.get("completion_tokens")
        total_t = e.get("total_tokens")
        cost = e.get("cost_usd")
        model = e.get("model")

        if prompt_t is not None or compl_t is not None or total_t is not None:
            any_token_info = True
            if isinstance(prompt_t, int):
                total_prompt += prompt_t
            if isinstance(compl_t, int):
                total_completion += compl_t
            if isinstance(total_t, int):
                total_tokens += total_t

        if cost is not None:
            any_cost_info = True
            try:
                total_cost += float(cost)
            except Exception:
                pass

        if model:
            models.add(str(model))

    result: Dict[str, Any] = {
        "total_prompt_tokens": total_prompt if any_token_info else None,
        "total_completion_tokens": total_completion if any_token_info else None,
        "total_tokens": total_tokens if any_token_info else None,
        "total_cost_usd": total_cost if any_cost_info else None,
        "models_used": ", ".join(sorted(models)) if models else None,
    }
    return result
