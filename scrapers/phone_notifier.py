"""
Texts new approved events to subscribers stored in Supabase.

Reads subscribers + events from Supabase, filters by each subscriber's
company/category preferences, and sends ONE batched SMS per subscriber via
Twilio. notification_log guarantees nobody is texted twice about the same event.

Safe no-op until SUPABASE_* and TWILIO_* are set in scrapers/.env — prints a
skip message and exits 0 so the pipeline keeps working before credentials exist.

Usage:
    python phone_notifier.py
"""

import os
import sys
from datetime import datetime

import db

MAX_EVENTS_PER_SMS = 5  # keep messages to a reasonable segment count

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

def short_date(starts_at: str, has_time: bool) -> str:
    try:
        dt = datetime.fromisoformat(starts_at)
    except (ValueError, TypeError):
        return str(starts_at)
    day = f"{dt.strftime('%b')} {dt.day}"
    return f"{day} {dt.strftime('%I:%M%p').lstrip('0')}" if has_time else day

def matches(sub: dict, event: dict) -> bool:
    companies  = sub.get("companies") or []
    categories = sub.get("categories") or []
    if companies and event.get("company") not in companies:
        return False
    if categories and event.get("category") not in categories:
        return False
    return True

def build_sms(events: list[dict]) -> str:
    lines = [f"CareerEventBot: {len(events)} new event(s)"]
    for e in events[:MAX_EVENTS_PER_SMS]:
        lines.append(f"- {e['company']}: {e['event']} ({short_date(e['starts_at'], e.get('has_time'))})")
    if len(events) > MAX_EVENTS_PER_SMS:
        lines.append(f"...and {len(events) - MAX_EVENTS_PER_SMS} more")
    lines.append("Reply STOP to opt out.")
    return "\n".join(lines)

def main():
    if not db.is_configured():
        print("Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_KEY) — skipping phone notifications.")
        return
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
        print("Twilio not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER) — skipping phone notifications.")
        return

    subscribers = db.fetch_active_subscribers()
    if not subscribers:
        print("No active subscribers.")
        return

    events = db.fetch_approved_future_events()
    if not events:
        print("No approved upcoming events.")
        return

    already_sent = db.fetch_notified_pairs()

    from twilio.rest import Client
    twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    sent_count = 0
    for sub in subscribers:
        new_events = [
            e for e in events
            if matches(sub, e) and (sub["id"], e["id"]) not in already_sent
        ]
        if not new_events:
            continue

        body = build_sms(new_events)
        event_ids = [e["id"] for e in new_events]
        try:
            twilio.messages.create(
                to=sub["phone_number"], from_=TWILIO_FROM_NUMBER, body=body
            )
            status = "sent"
            sent_count += 1
            print(f"  [OK] {sub['phone_number']}: {len(new_events)} event(s)")
        except Exception as exc:
            status = "failed"
            print(f"  [!] {sub['phone_number']}: {exc}")

        # Log immediately after each send so a crash mid-run can't double-text
        db.log_notifications(sub["id"], event_ids, status=status)

    print(f"\nDone. SMS sent to {sent_count} subscriber(s).")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Phone alerts must never break the main pipeline
        print(f"[!] Phone notifier error: {exc}")
        sys.exit(1)
