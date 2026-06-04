import json
import os
from pathlib import Path

_CONFIG_PATH = Path(os.environ.get("APPDATA", Path.home())) / "takt" / "settings.json"

_DEFAULTS = {
    "api_url": "http://127.0.0.1:8080",
    "theme": "dark",
    "palette": "Donker",
    "default_context": None,
    "font_family": "Segoe UI",
    "font_size": 10,
    "item_spacing": 12,
    "filter_context_ids": [],
    "filter_root_ids": [],
    "db_path": "",
}


def load() -> dict:
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def save(settings: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
