"""
Posts new events from data/events.yaml to Discord via webhook.
Tracks already-posted events in data/sent_events.yaml to avoid duplicates.

Usage:
    python discord_notifier.py
"""

import os
import sys
import time
import yaml
import requests
from datetime import date, datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

from common import event_key, load_yaml, is_future, format_date

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(Path(__file__).parent / ".env")

WEBHOOK_URL  = os.getenv("DISCORD_WEBHOOK_URL")
EVENTS_PATH  = Path(__file__).parent.parent / "data" / "events.yaml"
SENT_PATH    = Path(__file__).parent.parent / "data" / "sent_events.yaml"

# Embed colour per company (hex → int)
COMPANY_COLORS = {
    "Capital One": 0xD03027,   # Capital One red
    "Google":      0x4285F4,
    "Microsoft":   0x00A4EF,
    "Meta":        0x0866FF,
    "Amazon":      0xFF9900,
    "Apple":       0x555555,
    "Netflix":     0xE50914,
    "Nvidia":      0x76B900,
    "Salesforce":  0x00A1E0,
    "Adobe":       0xFF0000,
    "Intel":       0x0071C5,
    "IBM":         0x1F70C1,
    "Cisco":       0x1BA0D7,
    "Oracle":      0xF80000,
    "Spotify":     0x1DB954,
    "Airbnb":      0xFF5A5F,
    "Uber":        0x000000,
    "Stripe":      0x635BFF,
    "Palantir":    0x101010,
    "Lockheed Martin": 0x003087,
    "Deloitte":    0x86BC25,
}
DEFAULT_COLOR = 0x5865F2  # Discord blurple

TAG_EMOJI = {
    "info-session":  "📢",
    "internship":    "🎓",
    "new-grad":      "🎉",
    "career-fair":   "🏢",
    "tech-talk":     "💡",
    "networking":    "🤝",
    "hiring-event":  "📋",
    "hackathon":     "💻",
}

def save_sent(sent: list[str]):
    with open(SENT_PATH, "w") as f:
        yaml.dump({"sent": sent}, f, allow_unicode=True)

def build_embed(event: dict) -> dict:
    company  = event.get("company", "")
    title    = event.get("event", "")
    link     = event.get("link", "")
    location = event.get("location", "Virtual")
    tags     = event.get("tags", [])
    date_str = event.get("date", "")

    tag_line = "  ".join(f"{TAG_EMOJI.get(t, '🏷️')} {t}" for t in tags) if tags else ""
    color    = COMPANY_COLORS.get(company, DEFAULT_COLOR)

    embed = {
        "title":       title,
        "url":         link,
        "color":       color,
        "fields": [
            {"name": "🏢 Company",  "value": company,            "inline": True},
            {"name": "📅 Date",     "value": format_date(date_str), "inline": True},
            {"name": "📍 Location", "value": location,           "inline": True},
        ],
        "footer": {"text": "CareerEventWatcher • eightfold.ai"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if tag_line:
        embed["fields"].append({"name": "Tags", "value": tag_line, "inline": False})

    return embed

def post_batch(embeds: list[dict], content: str = "") -> bool:
    payload = {"embeds": embeds}
    if content:
        payload["content"] = content

    resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    if resp.status_code in (200, 204):
        return True
    print(f"  [!] Discord returned {resp.status_code}: {resp.text[:200]}")
    return False

def main():
    if not WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL not set in .env")
        sys.exit(1)

    events_data = load_yaml(EVENTS_PATH)
    # events.yaml is a list at top level
    if isinstance(events_data, list):
        events = events_data
    else:
        print("ERROR: events.yaml is not a list")
        sys.exit(1)

    sent_data = load_yaml(SENT_PATH)
    sent_keys = set(sent_data.get("sent", []) if isinstance(sent_data, dict) else [])

    # Filter: future events not yet posted
    new_events = [
        e for e in events
        if is_future(e) and event_key(e) not in sent_keys
    ]

    if not new_events:
        print("No new events to post.")
        return

    print(f"Posting {len(new_events)} new event(s) to Discord...")

    # Send a header message first
    header_payload = {
        "content": f"## 📣 Career Events Update — {date.today().strftime('%B %d, %Y')}\n{len(new_events)} new event(s) found:"
    }
    requests.post(WEBHOOK_URL, json=header_payload, timeout=10)
    time.sleep(0.5)

    # Post in batches of 10 (Discord limit per message)
    posted_keys = []
    for i in range(0, len(new_events), 10):
        batch = new_events[i:i + 10]
        embeds = [build_embed(e) for e in batch]
        ok = post_batch(embeds)
        if ok:
            for e in batch:
                posted_keys.append(event_key(e))
                print(f"  [OK] {e.get('company')} - {e.get('event')}")
            # Save incrementally so a crash mid-run doesn't lose progress
            save_sent(list(sent_keys | set(posted_keys)))
        else:
            print(f"  [!] Batch {i//10 + 1} failed, skipping.")
        time.sleep(1)  # stay well under Discord rate limit

    print(f"\nDone. {len(posted_keys)} event(s) posted, {len(new_events) - len(posted_keys)} failed.")

if __name__ == "__main__":
    main()
