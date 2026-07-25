"""
Scrapes Eightfold.ai career event pages, handling multi-page results.
Companies are configured in config.yaml under `eightfold_pages`.

Usage:
    python eightfold_scraper.py
"""

import asyncio
import re
import yaml
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright

CONFIG_PATH = Path(__file__).parent / "config.yaml"
PENDING_PATH = Path(__file__).parent.parent / "data" / "events_pending.yaml"

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

def infer_tags(title: str) -> list[str]:
    t = title.lower()
    if any(k in t for k in ("job fair", "career fair", "hiring fair", "job expo")):
        return ["career-fair"]
    if any(k in t for k in ("workshop", "case interview", "coding assessment", "doing the math", "ace the")):
        return ["workshop"]
    if any(k in t for k in ("hackathon", "hack")):
        return ["hackathon"]
    if any(k in t for k in ("networking", "mixer", "meetup")):
        return ["networking"]
    return ["info-session"]

def parse_eightfold_date(dd: str, mmm: str, full_text: str) -> str:
    year_match = re.search(r"\b(202\d)\b", full_text)
    year = year_match.group(1) if year_match else str(datetime.now().year)
    month = MONTH_MAP.get(mmm.strip().lower()[:3], "01")
    day = dd.strip().zfill(2)
    return f"{year}-{month}-{day}"

def load_pending() -> list[dict]:
    if PENDING_PATH.exists():
        with open(PENDING_PATH) as f:
            return yaml.safe_load(f) or []
    return []

def save_pending(events: list[dict]):
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PENDING_PATH, "w") as f:
        yaml.dump(events, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

def dedup(events: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for e in events:
        key = (e.get("company", ""), e.get("event", ""), e.get("date", ""))
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out

async def get_page_count(page) -> int:
    """Return total number of pages from the pagination widget."""
    pager = await page.query_selector(".pagination-module_pager__KjXDQ")
    if not pager:
        return 1
    buttons = await pager.query_selector_all("button, li")
    numbers = []
    for btn in buttons:
        text = (await btn.inner_text()).strip()
        if text.isdigit():
            numbers.append(int(text))
    return max(numbers) if numbers else 1

def build_event_link(base_url: str, domain: str, href: str) -> str:
    """
    Convert the raw registration href into the canonical event link.
    Input:  /events/candidate/registration?plannedEventId=ABC
    Output: https://company.eightfold.ai/events/candidate?plannedEventId=ABC&domain=company.com
    """
    parsed = urlparse(href)
    event_id = parse_qs(parsed.query).get("plannedEventId", [None])[0]
    if event_id:
        return f"{base_url}/events/candidate?plannedEventId={event_id}&domain={domain}"
    # Fallback: just prepend base if it's a relative path
    return base_url + href if href.startswith("/") else href

async def scrape_cards(page, domain: str) -> list[dict]:
    """Extract all event cards visible on the current page."""
    base_url = "/".join(page.url.split("/")[:3])

    all_cards = await page.query_selector_all(".event-listing-page-card")
    cards = [
        c for c in all_cards
        if "thumbnail" not in (await c.get_attribute("class") or "")
        and "content" not in (await c.get_attribute("class") or "")
    ]

    results = []
    for card in cards:
        try:
            title_el = await card.query_selector(".event-title")
            dd_el    = await card.query_selector(".event-card-start-date-dd")
            mmm_el   = await card.query_selector(".event-card-start-date-mmm")
            loc_el   = await card.query_selector("[class*=locationText]")
            link_el  = await card.query_selector("a")

            title    = (await title_el.inner_text()).strip() if title_el else ""
            dd       = (await dd_el.inner_text()).strip()    if dd_el    else ""
            mmm      = (await mmm_el.inner_text()).strip()   if mmm_el   else ""
            location = (await loc_el.inner_text()).strip()   if loc_el   else "Virtual"
            href     = (await link_el.get_attribute("href")) if link_el  else ""

            if not title:
                continue

            full_text = await card.inner_text()
            date_str  = parse_eightfold_date(dd, mmm, full_text)

            if href:
                href = build_event_link(base_url, domain, href)

            results.append({
                "company":  "",  # filled in by caller
                "event":    title,
                "date":     date_str,
                "location": location or "Virtual",
                "link":     href or page.url,
                "tags":     infer_tags(title),
                "source":   "eightfold",
            })
        except Exception as e:
            print(f"    [!] Card parse error: {e}")
            continue

    return results

async def scrape_company(browser, company: str, base_url: str) -> list[dict]:
    page = await browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    all_results = []

    # Extract domain param from config URL (e.g. "capitalone.com")
    domain = parse_qs(urlparse(base_url).query).get("domain", [""])[0]

    try:
        # Load page 1
        await page.goto(base_url, timeout=25000, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        total_pages = await get_page_count(page)
        print(f"  {company}: {total_pages} page(s) found")

        # Page 1
        cards = await scrape_cards(page, domain)
        all_results.extend(cards)

        # Pages 2+
        for page_num in range(2, total_pages + 1):
            sep = "&" if "?" in base_url else "?"
            paged_url = f"{base_url}{sep}page={page_num}"
            await page.goto(paged_url, timeout=25000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            cards = await scrape_cards(page, domain)
            all_results.extend(cards)
            print(f"    Page {page_num}: {len(cards)} events")

    except Exception as e:
        print(f"  [!] Failed scraping {company}: {e}")
    finally:
        await page.close()

    # Tag company name onto each result
    for r in all_results:
        r["company"] = company

    print(f"  [{len(all_results)} total] {company}")
    return all_results

async def main():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    entries = config.get("eightfold_pages", [])
    if not entries:
        print("No eightfold_pages in config.yaml.")
        return

    existing = load_pending()
    new_events = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        for entry in entries:
            found = await scrape_company(browser, entry["company"], entry["url"])
            new_events.extend(found)
        await browser.close()

    combined = dedup(existing + new_events)
    added = len(combined) - len(existing)
    save_pending(combined)

    # Stage B dual-write: mirror scraped events into Supabase as pending.
    # No-op until SUPABASE_* credentials are configured; YAML stays authoritative.
    try:
        import db
        if db.is_configured():
            n = db.upsert_events(new_events, status="pending")
            print(f"Supabase: upserted {n} pending event(s)")
    except Exception as e:
        print(f"[!] Supabase upsert failed (YAML unaffected): {e}")

    print(f"\nDone. {added} new event(s) written to data/events_pending.yaml")
    print("Review it, then run:  python scrapers/merge_events.py")

if __name__ == "__main__":
    asyncio.run(main())
