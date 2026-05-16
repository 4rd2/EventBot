# CareerEventBot — Implementation Plan

## Goal
Aggregate upcoming career/recruiting events (info sessions, career fairs, hackathons, networking nights, etc.) from top companies and deliver them as Discord notifications with direct registration links.

---

## Current Project Structure

```
CareerEventBot/
├── PLAN.md
├── ReadMe.md
├── .gitignore
├── data/
│   ├── events.yaml          ← live approved events
│   └── sent_events.yaml     ← tracks what has been posted to Discord
└── scrapers/
    ├── .env                 ← DISCORD_WEBHOOK_URL (not committed)
    ├── .env.example         ← template for new contributors
    ├── config.yaml          ← Eightfold company URLs
    ├── requirements.txt
    ├── eightfold_scraper.py ← scrapes Eightfold career event pages (multi-page)
    ├── merge_events.py      ← review pending events, push approved to events.yaml
    ├── discord_notifier.py  ← posts new events to Discord via webhook
    └── run_all.py           ← full pipeline in one command
```

---

## Data Format

**File:** `data/events.yaml`

```yaml
- company: Capital One
  event: 'Capital One Strategy: Intro to Casing'
  date: '2026-05-20'
  location: Online
  link: https://capitalone.eightfold.ai/events/candidate?plannedEventId=LWmaXkGW&domain=capitalone.com
  tags:
  - info-session
```

| Field | Required | Notes |
|---|---|---|
| `company` | yes | Display name |
| `event` | yes | Event title |
| `date` | yes | ISO 8601 (`YYYY-MM-DD`) |
| `link` | yes | Direct registration link |
| `location` | no | "Online" or city |
| `tags` | no | new-grad, info-session, networking, hackathon, internship |

---

## Workflow (Manual Run)

```powershell
# Full pipeline: scrape → auto-approve → post to Discord
python scrapers/run_all.py --merge

# Step-by-step with manual review:
python scrapers/eightfold_scraper.py   # → data/events_pending.yaml
python scrapers/merge_events.py        # review each event Y/n
python scrapers/discord_notifier.py    # post only new events to Discord
```

The `sent_events.yaml` log ensures events are never double-posted across runs.

---

## Phase 1 — Capital One MVP  ✅ COMPLETE

- [x] Eightfold scraper — handles pagination, extracts title / date / location / link
- [x] Merge script — deduplicates, filters past events, interactive Y/n review
- [x] Discord notifier — posts rich embeds via webhook, tracks sent events
- [x] 18 Capital One events live in `events.yaml`

**Confirmed working Eightfold pages:**
- Capital One: `capitalone.eightfold.ai`

---

## Phase 2 — Automated Daily Scheduling

Run the full pipeline on a daily schedule with no manual intervention.

### 2.1 Options (pick one)

**Option A — Windows Task Scheduler** *(simplest, runs on your local machine)*
```powershell
# Run every day at 9am
schtasks /create /tn "CareerEventWatcher" ^
  /tr "python \"c:\Coding of All sorts\PersonalProjects\CareerEventWatcher\scrapers\run_all.py\" --merge" ^
  /sc daily /st 09:00
```

**Option B — GitHub Actions** *(runs in the cloud, free, recommended)*
```yaml
# .github/workflows/update-events.yml
on:
  schedule:
    - cron: '0 13 * * *'   # every day at 9am ET
  workflow_dispatch:        # also allow manual trigger from GitHub UI
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -r scrapers/requirements.txt
      - run: playwright install chromium
      - run: python scrapers/run_all.py --merge
      - run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add data/
          git diff --staged --quiet || git commit -m "auto: update events $(date +%F)"
          git push
    env:
      DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
```

### 2.2 Phase 2 Milestones
- [ ] Initialize git repo and push to GitHub
- [ ] Add GitHub Actions workflow file
- [ ] Store `DISCORD_WEBHOOK_URL` as a GitHub Actions secret
- [ ] Confirm automated daily runs post to Discord

---

## Phase 3 — Expand to More Companies

Add more companies by finding their career event pages and wiring them into the scraper.

### 3.1 Eightfold Companies to Investigate
Many companies use Eightfold.ai. Verify by visiting
`https://[company].eightfold.ai/events/open?domain=[company].com`.

| Company | Eightfold URL | Status |
|---|---|---|
| Capital One | capitalone.eightfold.ai | Live — 18 events |
| Microsoft | microsoft.eightfold.ai | Events found, non-US only |
| Netflix | netflix.eightfold.ai | Events found, verify relevance |
| Nvidia | nvidia.eightfold.ai | Events found, non-US only |

To add a company, add an entry to `scrapers/config.yaml` and run the pipeline.

### 3.2 Other Platforms to Scrape
Not all companies use Eightfold. Common alternatives:

| Platform | Example Companies | Approach |
|---|---|---|
| Handshake | Most universities + employers | Requires login — Playwright with auth |
| Bevy | Google, Salesforce dev events | Public pages, BeautifulSoup |
| Eventbrite | Many public events | Public API (free key) |
| Company career pages | Amazon, Apple, Meta | Custom per-site scraper |

### 3.3 Target Company List
1. Google
2. Microsoft *(non-US currently — monitor)*
3. Meta
4. Amazon
5. Apple
6. Netflix
7. Nvidia *(non-US currently — monitor)*
8. Salesforce
9. Adobe
10. Intel
11. IBM
12. Cisco
13. Oracle
14. Spotify
15. Airbnb
16. Uber
17. Stripe
18. Palantir
19. Lockheed Martin
20. Deloitte

### 3.4 Phase 3 Milestones
- [ ] Verify and add 5+ more companies to `config.yaml`
- [ ] Add scraper for at least one non-Eightfold platform
- [ ] Filter Discord posts by tag (e.g. only `new-grad` and `internship`)

---

## Phase 4 — Delivery Expansion

Once automated, extend how events are delivered.

### 4.1 Website (Optional)
A read-only public site rendering `events.yaml` — useful for sharing with others.
- Stack: plain HTML + vanilla JS (no framework, no build step)
- Hosting: GitHub Pages (free, auto-deploys on push to main)
- Features: filter by tag, sort by date, "SOON" badge for events within 14 days

### 4.2 Phone / SMS Notifications (Optional)
Push event alerts as text messages.
- **Twilio** — SMS API, free trial tier, ~$0.01/msg after
- **Pushover** — mobile push notifications, one-time $5 app fee, simpler than Twilio
- **ntfy.sh** — free, open-source push to phone app, zero cost

Recommended starting point: ntfy.sh (free, no card required, easy Python integration).

```python
import requests
requests.post("https://ntfy.sh/your-topic", data="New Capital One event: Strategy Workshop — Jun 1")
```

---

## Tech Stack Summary

| Layer | Current Choice | Notes |
|---|---|---|
| Data | YAML | Human-editable, git-diffable |
| Scraping | Python + Playwright | Handles JS-rendered Eightfold pages |
| Delivery | Discord webhook | Rich embeds, per-event tracking |
| Scheduling | Manual (run_all.py) | → Task Scheduler / GitHub Actions in Phase 3 |
| Website | Not built | Optional Phase 4 |
| Phone alerts | Not built | Optional Phase 4 |
