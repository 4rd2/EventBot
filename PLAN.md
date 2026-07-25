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

### 4.2 Supabase Backend — Events + Phone Subscribers

Move the data layer to **Supabase** (Postgres): events migrate out of the YAML files
into an `events` table, and phone subscribers live in a `subscribers` table so people
can sign up/unsubscribe without editing the repo. Supabase account credentials will be
added later — everything below is designed so the pipeline runs fine (Supabase steps
silently skip, YAML keeps working) until the credentials exist.

#### Architecture

```
                          ┌─────────────────────────────────┐
 eightfold_scraper.py ──► │           Supabase              │
      (upsert events)     │  events          subscribers ◄──│── signup form /
                          │  notification_log               │   dashboard insert
                          └───────┬─────────────────┬───────┘
                                  │                 │ service-role key
                                  ▼                 ▼
                        discord_notifier.py   phone_notifier.py ──► Twilio SMS ──► 📱
```

- **Supabase** = source of truth for *what* events exist and *who* gets notified.
- **SMS provider** = *how* the message is delivered. Supabase doesn't send SMS itself,
  so pick one: **Twilio** (real SMS, ~$0.01/msg, recommended), or **ntfy.sh**
  (free push app, no phone number needed) as a zero-cost fallback.
- `notification_log` replaces the `sent_events.yaml` pattern *per subscriber*, so each
  person gets each event exactly once even across daily CI runs. Discord posting state
  becomes a `discord_posted_at` column on the event row itself.

#### Database schema (run in Supabase SQL editor)

```sql
create table events (
  id                uuid primary key default gen_random_uuid(),
  company           text not null,
  event             text not null,               -- event title
  category          text,                        -- primary type: info-session, career-fair, …
  tags              text[] default '{}',         -- extra labels beyond category
  starts_at         timestamptz not null,        -- event date-time (UTC)
  has_time          boolean default false,       -- false = scraper only knew the date
  location          text default 'Online',
  link              text not null,               -- registration URL
  source            text default 'eightfold',    -- which scraper found it
  status            text default 'pending',      -- pending | approved | rejected
  discord_posted_at timestamptz,                 -- null = not yet posted to Discord
  created_at        timestamptz default now(),
  updated_at        timestamptz default now(),
  unique (company, event, starts_at)             -- dedup key, same as today's event_key
);
create index events_starts_at_idx on events (starts_at);

create table subscribers (
  id           uuid primary key default gen_random_uuid(),
  phone_number text unique not null,          -- E.164 format: +16145551234
  name         text,
  companies    text[] default '{}',           -- empty = all companies
  categories   text[] default '{}',           -- empty = all categories
  active       boolean default true,          -- soft unsubscribe
  created_at   timestamptz default now()
);

create table notification_log (
  id            bigint generated always as identity primary key,
  subscriber_id uuid references subscribers(id) on delete cascade,
  event_id      uuid references events(id) on delete cascade,
  sent_at       timestamptz default now(),
  status        text default 'sent',          -- sent | failed
  unique (subscriber_id, event_id)
);

-- RLS: pipeline uses the service-role key which bypasses RLS.
alter table events enable row level security;
alter table subscribers enable row level security;
alter table notification_log enable row level security;

-- Events are not sensitive — allow public read (feeds the Phase 4.1 website for free):
create policy "public read events" on events for select to anon using (status = 'approved');

-- (Later, for a public signup form) allow anonymous INSERT only — anon can never READ numbers:
-- create policy "public signup" on subscribers for insert to anon with check (true);
```

Schema notes:
- `starts_at` is a real timestamp — current YAML only has a date, so migrated rows get
  midnight ET with `has_time = false`; the scraper should start capturing event times
  where Eightfold provides them and set `has_time = true`.
- `category` (single) vs `tags` (many): existing YAML `tags` map as first tag → `category`,
  full list → `tags`. Subscribers filter on `category`, which keeps preferences simple.
- `status` replaces the `events_pending.yaml` / `events.yaml` split: scraper inserts as
  `pending`, merge/approve flips to `approved`, notifiers only ever read `approved`.

#### Migration plan (YAML → Supabase, in safe stages)

1. **Stage A — backfill:** one-off `scrapers/migrate_to_supabase.py` reads
   `data/events.yaml` + `data/sent_events.yaml`, upserts every event as `approved`,
   and sets `discord_posted_at = now()` for events already in the sent log
   (so nothing gets re-posted after cutover).
2. **Stage B — dual write:** scraper/merge upsert into Supabase
   (`on_conflict=company,event,starts_at`) *and* keep writing YAML. Run a few days,
   confirm parity.
3. **Stage C — cutover reads:** `discord_notifier.py` and `phone_notifier.py` read
   `approved` future events from Supabase instead of YAML.
4. **Stage D — retire YAML:** stop writing `events.yaml` / `sent_events.yaml` and drop the
   commit step from the GitHub Actions workflow — the repo stops needing daily data commits.
   (Optional: keep a nightly YAML export as a human-readable backup.)

Until credentials exist, all Supabase code paths detect missing env vars and no-op,
so Stages A–D only begin once the account info is added.

#### New script: `scrapers/phone_notifier.py`

1. Load env: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `TWILIO_ACCOUNT_SID`,
   `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`.
2. **If Supabase vars are missing → print "phone notifications not configured, skipping" and `exit 0`.**
   This lets the feature merge now and light up later when credentials are added.
3. Fetch `subscribers` where `active = true`, and `approved` events with `starts_at >= now()`.
4. For each subscriber: filter events by their `companies`/`categories` prefs (empty = all),
   drop events already in `notification_log` for that subscriber.
5. Send one concise SMS per subscriber batching their new events
   (SMS is per-message billing — batch, don't send one text per event):
   `"CareerEventBot: 3 new events — Capital One Strategy Workshop (Jun 1), … Reply STOP to opt out."`
6. Insert a `notification_log` row per (subscriber, event) with `sent`/`failed` status;
   write log rows immediately after each send so a crash doesn't cause double-texts.

#### Subscriber signup — API endpoint

How people sign up (web form, Discord command, etc.) is not decided yet, so the repo
ships a single **API endpoint** that any future frontend can call: a Supabase Edge
Function at `supabase/functions/subscribe/index.ts`.

- `POST https://<project>.supabase.co/functions/v1/subscribe`
- Body: `{"phone_number": "+16145551234", "name": "…", "companies": [], "categories": []}`
  (only `phone_number` required; bare 10-digit US numbers are normalized to `+1…`)
- Responses: `201 subscribed`, `200 already_subscribed` / `resubscribed`
  (duplicate numbers re-activate instead of erroring), `400` invalid phone.
- CORS-enabled; runs with the service-role key injected by Supabase — so the
  `subscribers` table needs **no** anon insert policy, and anon can never read numbers.

Deploy (once the Supabase account exists):

```bash
supabase functions deploy subscribe --no-verify-jwt   # public endpoint, no auth header needed
curl -X POST https://<project>.supabase.co/functions/v1/subscribe \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+16145551234", "name": "Test"}'
```

> If signup abuse becomes a concern later, add a shared-secret header check or
> switch `--no-verify-jwt` off and require the anon key as a bearer token.

#### File changes

| File | Change |
|---|---|
| `scrapers/db.py` | new — Supabase client + helpers (returns `None` if unconfigured) |
| `scrapers/migrate_to_supabase.py` | new — one-off Stage A backfill from YAML |
| `scrapers/phone_notifier.py` | new — subscriber fetch + Twilio send (skips if unconfigured) |
| `supabase/functions/subscribe/index.ts` | new — public signup API endpoint (Edge Function) |
| `scrapers/common.py` | new — shared `event_key`, `load_yaml`, `is_future`, `format_date` |
| `scrapers/eightfold_scraper.py` | Stage B: also upsert scraped events into Supabase |
| `scrapers/merge_events.py` | Stage B: approval flips `status` to `approved` in Supabase |
| `scrapers/discord_notifier.py` | Stage C: read events from Supabase, set `discord_posted_at` |
| `scrapers/run_all.py` | run phone notifier after Discord notifier |
| `scrapers/requirements.txt` | add `supabase>=2.0`, `twilio>=9.0` |
| `scrapers/.env.example` | add `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `TWILIO_*` placeholders |
| `.github/workflows/update-events.yml` | pass new secrets; Stage D: drop the data-commit step |

#### Security notes

- Use the **service-role** key only in CI secrets / local `.env` — never in a browser or committed file.
- Phone numbers are PII: keep RLS on, no public SELECT, delete rows on unsubscribe requests.
- Events are fine to expose read-only via the anon key (they're public info anyway).
- Include opt-out language in every SMS ("Reply STOP") — required for US SMS compliance,
  and Twilio handles STOP replies automatically.

#### Milestones

- [ ] Add `db.py`, `common.py`, `phone_notifier.py`, `migrate_to_supabase.py` (all safe no-ops without credentials)
- [ ] Add `supabase/functions/subscribe/index.ts` signup endpoint
- [ ] Add deps, `.env.example` entries, workflow env wiring
- [ ] Create Supabase project, run schema SQL *(waiting on Supabase account info)*
- [ ] Deploy the `subscribe` edge function, test with `curl`
- [ ] Add `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` (+ Twilio) as GitHub Actions secrets
- [ ] Stage A: run backfill, spot-check rows in the Supabase dashboard
- [ ] Stage B: dual-write from scraper/merge, confirm parity with YAML for a few days
- [ ] Stage C: notifiers read from Supabase; insert a test subscriber, confirm SMS
- [ ] Stage D: retire YAML writes + workflow commit step
- [ ] Confirm daily CI run texts new events with no duplicates

---

## Tech Stack Summary

| Layer | Current Choice | Notes |
|---|---|---|
| Data | YAML | Human-editable, git-diffable |
| Scraping | Python + Playwright | Handles JS-rendered Eightfold pages |
| Delivery | Discord webhook | Rich embeds, per-event tracking |
| Scheduling | Manual (run_all.py) | → Task Scheduler / GitHub Actions in Phase 3 |
| Website | Not built | Optional Phase 4 |
| Phone alerts | Planned — Supabase subscribers + Twilio SMS | Phase 4.2 |
| Subscriber store | Supabase (Postgres) | Credentials to be added |
