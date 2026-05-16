"""
Merges approved events from data/events_pending.yaml into data/events.yaml.
Deduplicates by (company, event title, date).
Clears events_pending.yaml after merging.

Usage:
    python merge_events.py                  # interactive review
    python merge_events.py --auto-approve   # skip prompts, merge everything
"""

import sys
import yaml
from pathlib import Path
from datetime import date

LIVE_PATH = Path(__file__).parent.parent / "data" / "events.yaml"
PENDING_PATH = Path(__file__).parent.parent / "data" / "events_pending.yaml"

AUTO_APPROVE = "--auto-approve" in sys.argv

def load_yaml(path: Path) -> list[dict]:
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or []
    return []

def save_yaml(path: Path, events: list[dict]):
    with open(path, "w") as f:
        yaml.dump(events, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

def event_key(e: dict) -> tuple:
    return (
        e.get("company", "").lower().strip(),
        e.get("event", "").lower().strip(),
        str(e.get("date", "")),
    )

def is_future(e: dict) -> bool:
    try:
        return date.fromisoformat(str(e.get("date", ""))) >= date.today()
    except (ValueError, TypeError):
        return True  # keep events with unparseable dates

def print_event(e: dict):
    print(f"  Company : {e.get('company', '')}")
    print(f"  Event   : {e.get('event', '')}")
    print(f"  Date    : {e.get('date', '')}")
    print(f"  Location: {e.get('location', '')}")
    print(f"  Link    : {e.get('link', '')}")
    print(f"  Tags    : {', '.join(e.get('tags', []))}")
    print(f"  Source  : {e.get('source', 'manual')}")

def prompt_approve(e: dict) -> bool:
    print()
    print_event(e)
    answer = input("  Approve? [Y/n/q] ").strip().lower()
    if answer == "q":
        print("Quitting — partial merge saved.")
        sys.exit(0)
    return answer != "n"

def main():
    pending = load_yaml(PENDING_PATH)
    if not pending:
        print("Nothing in events_pending.yaml — nothing to merge.")
        return

    live = load_yaml(LIVE_PATH)
    existing_keys = {event_key(e) for e in live}

    # Strip internal scraper field before publishing
    def clean(e: dict) -> dict:
        return {k: v for k, v in e.items() if k != "source"}

    approved = []
    skipped = 0
    duplicates = 0

    for e in pending:
        if not is_future(e):
            skipped += 1
            continue

        key = event_key(e)
        if key in existing_keys:
            duplicates += 1
            continue

        if AUTO_APPROVE:
            approved.append(clean(e))
            existing_keys.add(key)
        else:
            if prompt_approve(e):
                approved.append(clean(e))
                existing_keys.add(key)

    # Merge + re-sort by date
    merged = live + approved
    merged.sort(key=lambda e: str(e.get("date", "9999")))

    save_yaml(LIVE_PATH, merged)
    save_yaml(PENDING_PATH, [])  # clear pending

    print(f"\nMerge complete.")
    print(f"  {len(approved)} event(s) added to events.yaml")
    print(f"  {duplicates} duplicate(s) skipped")
    print(f"  {skipped} past event(s) dropped")
    print(f"  events_pending.yaml cleared")

if __name__ == "__main__":
    main()
