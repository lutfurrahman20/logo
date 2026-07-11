"""
Edmonton Elks (CFL) - Player Headshot Scraper (CFL)
Uses the CFL official website REST API to get the roster + headshot URLs.
"""

import re
import time
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
CFL_API    = "https://www.cfl.ca/wp-json/wp/v2/players"
TEAM_ABBR  = "EDM"
OUTPUT_DIR = Path("f:/logo/cfl_elks_player_logos")

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


def get_players() -> list[dict]:
    print(f"  Fetching roster for {TEAM_ABBR} from CFL API ...")
    players = []
    page = 1

    while True:
        resp = requests.get(
            CFL_API,
            params={"per_page": 100, "page": page},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code == 400:  # page out of range
            break
        resp.raise_for_status()

        data = resp.json()
        if not data:
            break

        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))

        for p in data:
            if p.get("team_abbreviation") != TEAM_ABBR:
                continue
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}"
            name = name.strip()
            img_url = p.get("url_profile_image", "")
            if name and img_url:
                players.append({"name": name, "img_url": img_url})

        print(f"    Page {page}/{total_pages} - {TEAM_ABBR} players so far: {len(players)}")

        if page >= total_pages:
            break
        page += 1
        time.sleep(0.1)

    return players


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
    print(f"  Edmonton Elks (CFL) - Player Headshot Scraper")
    print("=" * 60)
    print(f"  Output folder : {OUTPUT_DIR}\n")

    players = get_players()
    if not players:
        print("No players found from API.")
        return

    print(f"\n  Found {len(players)} players\n")
    print("Downloading headshots ...\n")

    results = {"downloaded": 0, "skipped": 0, "no_image": 0}

    for i, player in enumerate(players, 1):
        name     = player["name"]
        img_url  = player["img_url"]
        safe     = safe_filename(name)
        ext      = "png" if img_url.lower().endswith(".png") else "jpg"
        out_path = OUTPUT_DIR / f"{safe}.{ext}"

        print(f"[{i:>3}/{len(players)}] {name}")

        if out_path.exists() and out_path.stat().st_size > 1000:
            print("         Already exists - skipping")
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
