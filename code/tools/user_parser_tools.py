from langchain.tools import tool
from typing import Optional

@tool
def alias_to_canonical(word: str, registry: dict) -> str:
    """
    Maps a word (metric, dimension, or alias) to its canonical name using a registry.
    Args:
        word: The word to map (e.g., metric, dimension, or alias).
        registry: Dictionary containing 'aliases', 'metrics', and 'dimensions'.
    Returns:
        The canonical name if found, otherwise returns the original word.
    """
    aliases = registry.get('aliases', {})
    for canon, syns in aliases.items():
        if word.lower() == canon.lower() or word.lower() in [s.lower() for s in syns]:
            return canon
        if word.lower() in [m.lower() for m in registry.get('metrics', [])]:
            return word
        if word.lower() in [d.lower() for d in registry.get('dimensions', [])]:
            return word
    return word

@tool
def try_map_template(metric: Optional[str], time_grain: Optional[str], group_by_cnt: int, tmpl_rules: dict) -> Optional[str]:
    """
    Maps a metric, time grain, and group-by count to a template ID using template rules.
    Args:
        metric: The metric name to match.
        time_grain: The time grain (e.g., 'daily', 'monthly').
        group_by_cnt: Number of group-by dimensions.
        tmpl_rules: Dictionary containing template mapping rules.
    Returns:
        The template ID if a matching rule is found, otherwise None.
    """
    if not metric:
        return None
    for rule in tmpl_rules.get('rules', []):
        when = rule.get('when', {})
        if when.get('metric') == metric and when.get('time_grain') == time_grain and when.get('group_by_count') == group_by_cnt:
            return rule.get('template_id')
    return None


