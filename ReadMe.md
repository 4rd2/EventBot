# CareerEventBot

Scrapes upcoming career recruiting events from company event pages and posts them to a Discord channel via webhook. Built around the Eightfold.ai recruiting platform used by many major companies.

---

## Currently Tracking

| Company | Source | Events |
|---|---|---|
| Capital One | [capitalone.eightfold.ai](https://capitalone.eightfold.ai/events/open?domain=capitalone.com) | Info sessions, workshops, career fairs |

> To add more companies see the [Adding a Company](#adding-a-company) section below.

---

## How It Works

1. **Scrape** — Playwright headless browser hits Eightfold career event pages and pulls all upcoming events across all pages
2. **Review** — events land in `data/events_pending.yaml` for optional manual review before going live
3. **Merge** — approved events are written to `data/events.yaml`, deduped and sorted by date
4. **Notify** — new events are posted to Discord as rich embeds; a sent log prevents double-posting

---

## Setup

**Requirements:** Python 3.11+

```powershell
pip install -r scrapers/requirements.txt
playwright install chromium
```

Copy the example env file and add your Discord webhook URL:

```powershell
copy scrapers\.env.example scrapers\.env
```

Then open `scrapers/.env` and fill in your webhook:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

> Create a webhook in Discord under: Server Settings → Integrations → Webhooks → New Webhook

---

## Usage

**Full pipeline (recommended):**
```powershell
python scrapers/run_all.py --merge
```
Scrapes, auto-approves all future events, and posts new ones to Discord.

**Step-by-step with manual review:**
```powershell
python scrapers/eightfold_scraper.py   # fetch → data/events_pending.yaml
python scrapers/merge_events.py        # review each event Y/n
python scrapers/discord_notifier.py    # post only new events to Discord
```

**Post-only (skip scraping):**
```powershell
python scrapers/run_all.py --post-only
```

---

## Project Structure

```
CareerEventBot/
├── ReadMe.md
├── PLAN.md                  ← implementation plan and roadmap
├── .gitignore
├── data/
│   ├── events.yaml          ← live approved events
│   └── sent_events.yaml     ← tracks events already posted to Discord
└── scrapers/
    ├── .env                 ← your credentials (not committed)
    ├── .env.example         ← template for new contributors
    ├── config.yaml          ← list of Eightfold company URLs to scrape
    ├── requirements.txt
    ├── eightfold_scraper.py ← Playwright scraper, handles pagination
    ├── merge_events.py      ← dedup + approve events into events.yaml
    ├── discord_notifier.py  ← posts new events to Discord
    └── run_all.py           ← runs the full pipeline
```

---

## Adding a Company

1. Find the company's Eightfold events page — URL pattern:
   `https://[company].eightfold.ai/events/open?domain=[company].com`
2. Verify it loads events in a browser
3. Add an entry to `scrapers/config.yaml`:

```yaml
eightfold_pages:
  - company: Capital One
    url: https://capitalone.eightfold.ai/events/open?domain=capitalone.com
  - company: YourCompany
    url: https://yourcompany.eightfold.ai/events/open?domain=yourcompany.com
```

4. Run `python scrapers/run_all.py --merge`
5. Update the **Currently Tracking** table in this README

---

## Roadmap

See [PLAN.md](PLAN.md) for the full implementation plan.

| Phase | Goal | Status |
|---|---|---|
| 1 | Capital One scraper + Discord notifications | Complete |
| 2 | Automated daily scheduling (GitHub Actions) | Planned |
| 3 | Expand to more companies | Planned |
| 4 | Website and/or phone notifications | Future |
