"""
San Francisco 49ers - ACTIVE Player Headshot Scraper
Uses the ESPN public API to get the active roster + headshot URLs directly.
No Selenium needed — clean, fast, and always gets the correct per-player image.
"""

import re
import time
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_API   = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/sf/roster"
OUTPUT_DIR = Path("f:/logo/49ers_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
# ───────────────────────────────────────────────────────────────────────────────


def safe_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower()


def get_active_players() -> list[dict]:
    print("  Fetching roster from ESPN API ...")
    resp = requests.get(ESPN_API, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    ACTIVE_GROUPS = {"offense", "defense", "specialTeam"}

    players = []
    for group in data.get("athletes", []):
        if group.get("position", "") not in ACTIVE_GROUPS:
            continue
        for athlete in group.get("items", []):
            name     = athlete.get("fullName", "")
            headshot = athlete.get("headshot", "")
            if isinstance(headshot, dict):
                img_url = headshot.get("href", "")
            else:
                img_url = str(headshot) if headshot else ""
            if name and img_url:
                players.append({"name": name, "img_url": img_url})

    return players


def upgrade_url(url: str) -> str:
    m = re.search(r"img=([^&]+)", url)
    if m:
        return f"https://a.espncdn.com{m.group(1)}"
    return url


def download_image(url: str, filepath: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 1000:
            filepath.write_bytes(r.content)
            return True
        print(f"    WARNING HTTP {r.status_code} or tiny file - skipped")
    except Exception as e:
        print(f"    ERROR Download error: {e}")
    return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  SAN FRANCISCO 49ERS - Active Player Headshot Scraper")
    print("=" * 60)
    print(f"  Output folder : {OUTPUT_DIR}\n")

    players = get_active_players()
    if not players:
        print("No active players found from API.")
        return

    print(f"  Found {len(players)} active players\n")
    print("Downloading headshots ...\n")

    results = {"downloaded": 0, "skipped": 0, "no_image": 0}

    for i, player in enumerate(players, 1):
        name    = player["name"]
        img_url = upgrade_url(player["img_url"])
        safe    = safe_filename(name)
        ext     = "png" if img_url.lower().endswith(".png") else "jpg"
        out_path = OUTPUT_DIR / f"{safe}.{ext}"

        print(f"[{i:>3}/{len(players)}] {name}")

        if out_path.exists() and out_path.stat().st_size > 1000:
            print(f"         Already exists - skipping")
            results["skipped"] += 1
            continue

        print(f"         {img_url}")
        if download_image(img_url, out_path):
            size_kb = out_path.stat().st_size / 1024
            print(f"         Saved ({size_kb:.1f} KB)")
            results["downloaded"] += 1
        else:
            results["no_image"] += 1

        time.sleep(0.3)

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Downloaded : {results['downloaded']}")
    print(f"  Skipped    : {results['skipped']}")
    print(f"  No image   : {results['no_image']}")
    print(f"  Saved to   : {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
