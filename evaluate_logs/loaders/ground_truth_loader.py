from pathlib import Path
import yaml
from typing import Dict


def load_ground_truth(path: Path) -> Dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("ground_truth.yaml must contain a mapping from test_id to case definitions")
    return data
