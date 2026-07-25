"""
One-off Stage A backfill: copy data/events.yaml into the Supabase events table.

Every event is upserted as status=approved (they were already approved into
events.yaml). Events found in data/sent_events.yaml get discord_posted_at
stamped so nothing gets re-posted to Discord after the cutover.

Idempotent — safe to re-run. Skips with exit 0 if Supabase isn't configured.

Usage:
    python migrate_to_supabase.py
"""

import sys
from datetime import datetime, timezone

import db
from common import EVENTS_PATH, SENT_PATH, event_key, load_yaml

def main():
    if not db.is_configured():
        print("Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_KEY) — nothing to migrate.")
        return

    events = load_yaml(EVENTS_PATH, default=[])
    if not isinstance(events, list) or not events:
        print("No events in data/events.yaml — nothing to migrate.")
        return

    sent_data = load_yaml(SENT_PATH)
    sent_keys = set(sent_data.get("sent", []) if isinstance(sent_data, dict) else [])
    posted_at = datetime.now(timezone.utc).isoformat()

    rows, skipped = [], 0
    for e in events:
        row = db.yaml_event_to_row(e, status="approved")
        if row is None:
            skipped += 1
            print(f"  [!] Skipping unparseable event: {e.get('event', '?')} ({e.get('date', '?')})")
            continue
        if event_key(e) in sent_keys:
            row["discord_posted_at"] = posted_at
        rows.append(row)

    client = db.get_client()
    client.table("events").upsert(rows, on_conflict="company,event,starts_at").execute()

    already_posted = sum(1 for r in rows if r.get("discord_posted_at"))
    print(f"Migrated {len(rows)} event(s) to Supabase "
          f"({already_posted} marked as already posted to Discord, {skipped} skipped).")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[!] Migration failed: {exc}")
        sys.exit(1)
