"""
Chicago Cubs - Full Roster Player Headshot Scraper (MLB)
Fetches the 40-man roster from the MLB Stats API, resolves ESPN athlete IDs
via ESPN search, and downloads headshots from the ESPN CDN (with MLB CDN fallback).
"""

import re
import time
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
MLB_ROSTER_API  = "https://statsapi.mlb.com/api/v1/teams/112/roster/40Man"
ESPN_ROSTER_API = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/16/roster"
ESPN_SEARCH_API = "https://site.api.espn.com/apis/search/v2"
OUTPUT_DIR      = Path("f:/logo/chicago_cubs_mlb_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
# ───────────────────────────────────────────────────────────────────────────────


def safe_filename(name: str) -> str:
    """Remove characters invalid on Windows; keep spaces, dots, hyphens."""
    return re.sub(r'[\\/:*?"<>|]', "", name.strip())


def get_espn_active_roster() -> dict:
    """Return {player_name: headshot_url} for the ESPN active roster."""
    resp = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    result = {}
    for group in data.get("athletes", []):
        for item in group.get("items", [group]):
            name = item.get("displayName", "")
            headshot = item.get("headshot", {})
            img_url = headshot.get("href", "") if isinstance(headshot, dict) else (str(headshot) if headshot else "")
            if name and img_url:
                result[name] = img_url
    return result


def get_mlb_40man_roster() -> list:
    """Return [{name, mlb_id}] for the full 40-man roster from MLB Stats API."""
    resp = requests.get(MLB_ROSTER_API, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    players = []
    for entry in data.get("roster", []):
        person = entry.get("person", {})
        name   = person.get("fullName", "")
        mlb_id = person.get("id")
        if name:
            players.append({"name": name, "mlb_id": mlb_id})
    return players


def espn_search_headshot(name: str) -> str:
    """Search ESPN for a player by name; return ESPN CDN headshot URL or ''."""
    params = {"query": name, "sport": "baseball", "league": "mlb", "limit": "5"}
    try:
        resp = requests.get(ESPN_SEARCH_API, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        for rg in resp.json().get("results", []):
            if rg.get("type") != "player":
                continue
            for item in rg.get("contents", []):
                if item.get("type") != "player":
                    continue
                m = re.search(r"a:(\d+)", item.get("uid", ""))
                if m:
                    espn_id = m.group(1)
                    return f"https://a.espncdn.com/i/headshots/mlb/players/full/{espn_id}.png"
    except Exception as exc:
        print(f"    ESPN search error for {name!r}: {exc}")
    return ""


def mlb_cdn_headshot(mlb_id) -> str:
    return (
        f"https://img.mlbstatic.com/mlb-photos/image/upload/"
        f"d_people:generic:headshot:67:current.png/w_213,q_auto:best/"
        f"v1/people/{mlb_id}/headshot/67/current"
    )


def download_image(url: str, filepath: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 1000:
            filepath.write_bytes(r.content)
            return True
        print(f"    WARNING  HTTP {r.status_code} or tiny file")
    except Exception as exc:
        print(f"    ERROR    {exc}")
    return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  Chicago Cubs (MLB) - Full Roster Headshot Scraper")
    print("=" * 60)
    print(f"  Output folder : {OUTPUT_DIR}")
    print()

    print("  Step 1: Loading ESPN active roster ...")
    espn_roster = get_espn_active_roster()
    print(f"          {len(espn_roster)} players found")
    print()

    print("  Step 2: Loading 40-man roster from MLB Stats API ...")
    mlb_roster = get_mlb_40man_roster()
    print(f"          {len(mlb_roster)} players found")
    print()

    results = {"downloaded": 0, "skipped": 0, "no_image": 0}
    total = len(mlb_roster)
    print("Downloading headshots ...")
    print()

    for i, player in enumerate(mlb_roster, 1):
        name   = player["name"]
        mlb_id = player["mlb_id"]
        safe   = safe_filename(name)
        out_path = OUTPUT_DIR / f"{safe}.png"

        print(f"[{i:>3}/{total}] {name}")

        if out_path.exists() and out_path.stat().st_size > 1000:
            print("         Already exists - skipping")
            results["skipped"] += 1
            continue

        # Priority 1: ESPN active roster (URL already known)
        img_url = espn_roster.get(name, "")
        use_mlb = False

        # Priority 2: ESPN search API
        if not img_url:
            print("         Searching ESPN ...")
            img_url = espn_search_headshot(name)
            time.sleep(0.5)

        # Priority 3: MLB CDN fallback
        if not img_url and mlb_id:
            img_url = mlb_cdn_headshot(mlb_id)
            use_mlb = True

        if not img_url:
            print("         No image URL found")
            results["no_image"] += 1
            continue

        source = "MLB CDN" if use_mlb else "ESPN"
        print(f"         [{source}] {img_url}")

        if download_image(img_url, out_path):
            size_kb = out_path.stat().st_size / 1024
            print(f"         Saved ({size_kb:.1f} KB)")
            results["downloaded"] += 1
        else:
            # Retry with MLB CDN if ESPN failed
            if not use_mlb and mlb_id:
                fallback = mlb_cdn_headshot(mlb_id)
                print(f"         Fallback to MLB CDN: {fallback}")
                if download_image(fallback, out_path):
                    size_kb = out_path.stat().st_size / 1024
                    print(f"         Saved via MLB CDN ({size_kb:.1f} KB)")
                    results["downloaded"] += 1
                    time.sleep(0.3)
                    continue
            results["no_image"] += 1

        time.sleep(0.3)

    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Downloaded : {results['downloaded']}")
    print(f"  Skipped    : {results['skipped']}")
    print(f"  No image   : {results['no_image']}")
    print(f"  Saved to   : {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
