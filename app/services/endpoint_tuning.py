import json
from pathlib import Path

from app.core.paths import MOONSHOT_DATA_ROOT


ENDPOINT_DIR = MOONSHOT_DATA_ROOT / "connectors-endpoints"


def apply_endpoint_thread_count(endpoint_ids: list[str], thread_count: int) -> None:
    safe_count = max(1, min(20, int(thread_count or 1)))
    for endpoint_id in endpoint_ids:
        path = ENDPOINT_DIR / f"{endpoint_id}.json"
        if not path.exists() or not path.is_file():
            continue
        endpoint = json.loads(path.read_text(encoding="utf-8-sig"))
        endpoint["max_concurrency"] = safe_count
        endpoint["max_calls_per_second"] = safe_count
        path.write_text(json.dumps(endpoint, indent=2, ensure_ascii=False), encoding="utf-8")
