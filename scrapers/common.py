"""
Shared helpers used by the notifier and migration scripts.
"""

from datetime import date
from pathlib import Path

import yaml

DATA_DIR    = Path(__file__).parent.parent / "data"
EVENTS_PATH = DATA_DIR / "events.yaml"
SENT_PATH   = DATA_DIR / "sent_events.yaml"

def event_key(e: dict) -> str:
    return f"{e.get('company','')}|{e.get('event','')}|{e.get('date','')}"

def load_yaml(path: Path, default=None):
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f)
            if data is not None:
                return data
    return {} if default is None else default

def is_future(e: dict) -> bool:
    try:
        return date.fromisoformat(str(e.get("date", ""))) >= date.today()
    except (ValueError, TypeError):
        return True

def format_date(date_str) -> str:
    try:
        d = date.fromisoformat(str(date_str))
        return d.strftime("%A, %B %-d, %Y")
    except Exception:
        # %-d not supported on Windows — fallback
        try:
            d = date.fromisoformat(str(date_str))
            return d.strftime("%A, %B %d, %Y").replace(" 0", " ")
        except Exception:
            return str(date_str)
