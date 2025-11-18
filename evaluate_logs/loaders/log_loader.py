import json
from collections import defaultdict
from typing import Dict, List


def load_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def load_runs(path: str) -> Dict[str, List[dict]]:
    runs = defaultdict(list)
    for e in load_jsonl(path):
        tid = e.get("test_id") or e.get("query_hash")
        if not tid:
            continue
        runs[tid].append(e)
    return runs
