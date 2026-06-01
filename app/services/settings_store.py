import json
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT


SETTINGS_DIR = PROJECT_ROOT / "data" / "settings"
SETTINGS_FILE = SETTINGS_DIR / "app-settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "light",
}


class SettingsStore:
    def __init__(self, path: Path = SETTINGS_FILE) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get(self) -> dict[str, Any]:
        if not self.path.exists():
            self.save(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)
        try:
            settings = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            settings = {}
        return {**DEFAULT_SETTINGS, **settings}

    def save(self, settings: dict[str, Any]) -> dict[str, Any]:
        normalized = {**DEFAULT_SETTINGS, **settings}
        if normalized["theme"] not in {"light", "dark"}:
            normalized["theme"] = DEFAULT_SETTINGS["theme"]
        self.path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
        return normalized

    def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        return self.save({**self.get(), **changes})
