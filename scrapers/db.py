"""
Supabase client + data-access helpers.

Safe to use before the Supabase project exists: is_configured() is False and
get_client() returns None until SUPABASE_URL / SUPABASE_SERVICE_KEY are set in
scrapers/.env (or the environment), so callers can skip their Supabase steps.

Schema lives in PLAN.md §4.2 (events / subscribers / notification_log).
"""

import os
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

EVENT_TZ = ZoneInfo("America/New_York")

_client = None

def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)

def get_client():
    """Return a cached Supabase client, or None if credentials aren't set."""
    global _client
    if not is_configured():
        return None
    if _client is None:
        from supabase import create_client  # imported lazily so the no-op path needs no dep
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client

def event_starts_at(e: dict) -> str | None:
    """YAML events carry only a date — store midnight ET so the dedup key is stable."""
    try:
        d = date.fromisoformat(str(e.get("date", "")))
    except (ValueError, TypeError):
        return None
    return datetime(d.year, d.month, d.day, tzinfo=EVENT_TZ).isoformat()

def yaml_event_to_row(e: dict, status: str = "pending") -> dict | None:
    starts_at = event_starts_at(e)
    if not starts_at or not e.get("event") or not e.get("company"):
        return None
    tags = e.get("tags") or []
    return {
        "company":   e["company"],
        "event":     e["event"],
        "category":  tags[0] if tags else None,
        "tags":      tags,
        "starts_at": starts_at,
        "has_time":  False,
        "location":  e.get("location") or "Online",
        "link":      e.get("link") or "",
        "source":    e.get("source", "eightfold"),
        "status":    status,
    }

def upsert_events(events: list[dict], status: str = "pending") -> int:
    """Insert scraped events, leaving rows that already exist untouched
    (so a re-scrape never resets an approved event back to pending)."""
    client = get_client()
    rows = [r for e in events if (r := yaml_event_to_row(e, status))]
    if not client or not rows:
        return 0
    client.table("events").upsert(
        rows, on_conflict="company,event,starts_at", ignore_duplicates=True
    ).execute()
    return len(rows)

def approve_events(events: list[dict]) -> int:
    """Upsert approved events, overwriting status (pending -> approved)."""
    client = get_client()
    rows = [r for e in events if (r := yaml_event_to_row(e, status="approved"))]
    if not client or not rows:
        return 0
    client.table("events").upsert(rows, on_conflict="company,event,starts_at").execute()
    return len(rows)

def fetch_approved_future_events() -> list[dict]:
    client = get_client()
    if not client:
        return []
    resp = (
        client.table("events")
        .select("*")
        .eq("status", "approved")
        .gte("starts_at", datetime.now(timezone.utc).isoformat())
        .order("starts_at")
        .execute()
    )
    return resp.data or []

def fetch_active_subscribers() -> list[dict]:
    client = get_client()
    if not client:
        return []
    resp = client.table("subscribers").select("*").eq("active", True).execute()
    return resp.data or []

def fetch_notified_pairs() -> set[tuple[str, str]]:
    """(subscriber_id, event_id) pairs already sent, to prevent duplicate texts."""
    client = get_client()
    if not client:
        return set()
    resp = (
        client.table("notification_log")
        .select("subscriber_id,event_id")
        .eq("status", "sent")
        .execute()
    )
    return {(r["subscriber_id"], r["event_id"]) for r in (resp.data or [])}

def log_notifications(subscriber_id: str, event_ids: list[str], status: str = "sent"):
    client = get_client()
    if not client or not event_ids:
        return
    rows = [
        {"subscriber_id": subscriber_id, "event_id": eid, "status": status}
        for eid in event_ids
    ]
    # Overwrite on conflict so a retry after a failed send upgrades failed -> sent
    client.table("notification_log").upsert(
        rows, on_conflict="subscriber_id,event_id"
    ).execute()
