"""
Scrape your public contribution calendar - no token, no GraphQL.
GitHub serves it as HTML at https://github.com/users/<username>/contributions

Writes data/contributions.json with raw days + derived stats.
Usage: python scripts/fetch_contributions.py
"""
import json
import os
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import config

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"


def username() -> str:
    u = os.environ.get("PROFILE_USER") or config.USERNAME
    if not u or u == "YOUR_GITHUB_USERNAME":
        # inside GitHub Actions the repo owner is your username
        u = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    if not u:
        raise SystemExit("Set USERNAME in scripts/config.py")
    return u


def parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # tooltips hold the exact counts: "5 contributions on May 3rd."
    tips = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        m = re.match(r"\s*(\d[\d,]*|No)\s+contribution", tip.get_text())
        if target and m:
            tips[target] = 0 if m.group(1) == "No" else int(m.group(1).replace(",", ""))

    days = []
    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        level = int(cell.get("data-level", 0))
        count = tips.get(cell.get("id"))
        if count is None:  # older markup kept the count on the cell
            count = int(cell.get("data-count", 0) or 0)
        days.append({"date": cell["data-date"], "count": count, "level": level})

    days.sort(key=lambda d: d["date"])
    if not days:
        raise SystemExit("No contribution cells found - GitHub markup may have changed.")
    return days


def stats(days: list[dict]) -> dict:
    counts = [d["count"] for d in days]
    today = date.today().isoformat()

    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)

    # current streak: count back from the latest day; today with 0 doesn't break it yet
    current = 0
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        elif d["date"] == today and current == 0:
            continue
        else:
            break

    best = max(days, key=lambda d: d["count"])
    monthly = defaultdict(int)
    for d in days:
        monthly[d["date"][:7]] += d["count"]

    return {
        "total": sum(counts),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "active_days": sum(1 for c in counts if c > 0),
        "monthly": dict(sorted(monthly.items())),
    }


def main():
    user = username()
    url = f"https://github.com/users/{user}/contributions"
    r = requests.get(url, timeout=30, headers={"User-Agent": "profile-art-bot"})
    r.raise_for_status()
    days = parse(r.text)
    data = {"username": user, "fetched": date.today().isoformat(),
            "stats": stats(days), "days": days}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    s = data["stats"]
    print(f"✓ {user}: {s['total']} contributions, streak {s['current_streak']} "
          f"(longest {s['longest_streak']}) -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
