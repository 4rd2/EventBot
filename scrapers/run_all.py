"""
Full pipeline: scrape → merge → post to Discord.

Usage:
    python run_all.py                  # scrape only, leave pending for manual review
    python run_all.py --merge          # scrape + auto-approve merge + post to Discord
    python run_all.py --post-only      # skip scraping, just post unposted events to Discord
"""

import sys
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
AUTO_MERGE  = "--merge" in sys.argv
POST_ONLY   = "--post-only" in sys.argv

def run(label: str, script: Path, *args):
    print(f"\n{'='*50}")
    print(f"Running: {label}")
    print('='*50)
    result = subprocess.run([sys.executable, str(script), *args])
    if result.returncode != 0:
        print(f"[!] {label} exited with code {result.returncode}")

if not POST_ONLY:
    run("Eightfold scraper", HERE / "eightfold_scraper.py")

    if AUTO_MERGE:
        run("Merge (auto-approve)", HERE / "merge_events.py", "--auto-approve")
    else:
        print(f"\n{'='*50}")
        print("Scraping done. Review data/events_pending.yaml then run:")
        print("  python scrapers/merge_events.py")
        print("  python scrapers/discord_notifier.py")
        sys.exit(0)

run("Discord notifier", HERE / "discord_notifier.py")
