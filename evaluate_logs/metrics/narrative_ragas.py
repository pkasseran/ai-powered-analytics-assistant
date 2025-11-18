from typing import Dict, Any, List, Optional
from loaders.sqlalchemy_client import SQLAlchemyClient


def _extract_narrative_text(events: List[Dict[str, Any]]) -> Optional[str]:
    for e in events:
        if "narrative" in e:
            return e["narrative"]
        if "narrative_text" in e:
            return e["narrative_text"]
    return None


def _get_ground_truth_rows(gt_case: Dict[str, Any], db: SQLAlchemyClient):
    if not gt_case:
        return []
    reference_sql = gt_case.get("reference_sql")
    if not reference_sql:
        return []
    try:
        return db.run_sql(reference_sql)
    except Exception:
        return []


def evaluate_narrative_quality(events: List[Dict[str, Any]], gt_case: Dict[str, Any] | None, db: SQLAlchemyClient) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "narrative_present": None,
        "narrative_length_chars": None,
        "narrative_coverage_score": None,
    }
    narrative = _extract_narrative_text(events)
    if not narrative:
        return result

    result["narrative_present"] = True
    result["narrative_length_chars"] = len(narrative)

    gt_rows = _get_ground_truth_rows(gt_case or {}, db)
    key_terms = set()
    for r in gt_rows:
        for k, v in r.items():
            if isinstance(v, str) and len(v) > 2:
                key_terms.add(v)
    if not key_terms:
        return result

    narrative_lower = narrative.lower()
    hits = sum(1 for term in key_terms if term.lower() in narrative_lower)
    coverage = hits / len(key_terms) if key_terms else 0.0
    result["narrative_coverage_score"] = coverage
    return result
