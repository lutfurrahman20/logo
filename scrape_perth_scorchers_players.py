"""
Perth Scorchers BBL Player Jersey Image Downloader
Fetches full-body jersey images from perthscorchers.com.au
Saves as lowercase_underscore filenames.
"""

import requests
import re
import time
from pathlib import Path

OUTPUT_DIR = Path("f:/logo/perth_scorchers_players")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.perthscorchers.com.au/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SOURCE_URL = "https://www.perthscorchers.com.au/players/bbl-players"

# Requested players (display name → save filename)
REQUESTED_PLAYERS = [
    "Aaron Hardie",
    "Andrew Tye",
    "Ashton Agar",
    "Ashton Turner",
    "Brody L Couch",
    "Bryce Jackson",
    "Cameron Gannon",
    "Cooper Connolly",
    "Corey Rocchiccioli",
    "David Payne",
    "Finn Allen",
    "Jason Behrendorff",
    "Joel Paris",
    "Josh Inglis",
    "Keaton Jennings",
    "Lance Morris",
    "Laurie Evans",
    "Mahli Beardman",
    "Marcus Harris",
    "Matthew Hurst",
    "Matthew Kelly",
    "Matthew Spoors",
    "Mitchell Marsh",
    "Nick Hobson",
    "Sam Fanning",
    "Zak Crawley",
]


def name_to_filename(name: str) -> str:
    return name.lower().replace(" ", "_") + ".png"


def normalize(name: str) -> str:
    """Lowercase, strip punctuation for fuzzy matching."""
    return re.sub(r"[^a-z ]", "", name.lower()).strip()


def fetch_player_images(html: str) -> dict[str, str]:
    """
    Extract all (name → image_url) from the page.
    Two strategies:
      1. Pod blocks: title attr + srcset inside
      2. Fallback: infer name from image filename for pods without images
    CDN requires ?width= param, so we append ?width=560&height=668 (highest 2x res).
    """
    players: dict[str, str] = {}

    def with_size(url: str) -> str:
        return url + "?width=560&height=668"

    # Strategy 1: pods with images
    pod_blocks = re.findall(
        r"o-person-pod__inner[^>]*title='([^']+)'(.*?)o-person-pod__name",
        html,
        re.DOTALL,
    )
    for name, block in pod_blocks:
        m = re.search(
            r'srcset="(https://resources\.perth-scorchers\.pulselive\.com/photo-resources/[^?"]+)',
            block,
        )
        if not m:
            m = re.search(
                r'src="(https://resources\.perth-scorchers\.pulselive\.com/photo-resources/[^?"]+)',
                block,
            )
        if m:
            players[name.strip()] = with_size(m.group(1))

    # Strategy 2: srcset URLs not yet mapped – infer name from filename
    all_srcsets = re.findall(
        r'srcset="(https://resources\.perth-scorchers\.pulselive\.com/photo-resources/[^?"]+)',
        html,
    )
    mapped_base_urls = {u.split("?")[0] for u in players.values()}
    for url in all_srcsets:
        if url in mapped_base_urls:
            continue
        # Derive a human name from the filename:
        # e.g. "Brody-Couch-13-CLIP-CROP-WEB.png" → "Brody Couch"
        fname = url.split("/")[-1].replace(".png", "")
        parts = fname.split("-")
        # Take leading capitalised words as the name (stop at numbers / short tokens)
        name_parts = []
        for p in parts:
            if re.match(r"^\d+$", p):
                break
            if p.upper() == p and len(p) > 2:  # all-caps word like CROP/CLIP/WEB
                break
            name_parts.append(p)
        inferred_name = " ".join(name_parts)
        if inferred_name:
            players[inferred_name] = with_size(url)
            mapped_base_urls.add(url)

    return players


def best_match(requested: str, available: dict[str, str]) -> tuple[str, str] | None:
    """Find the best matching player from the available dict."""
    req_norm = normalize(requested)
    for avail_name, url in available.items():
        av_norm = normalize(avail_name)
        # Exact normalised match
        if req_norm == av_norm:
            return avail_name, url
        # "Mitchell Marsh" ↔ "Mitch Marsh" — first-name abbreviation
        req_parts = req_norm.split()
        av_parts = av_norm.split()
        if len(req_parts) >= 2 and len(av_parts) >= 2:
            # Last names match AND first names share a prefix
            if req_parts[-1] == av_parts[-1] and (
                req_parts[0].startswith(av_parts[0])
                or av_parts[0].startswith(req_parts[0])
            ):
                return avail_name, url
        # "Brody L Couch" ↔ "Brody Couch" — middle initial
        req_words = [w for w in req_parts if len(w) > 1]
        av_words = [w for w in av_parts if len(w) > 1]
        if req_words == av_words:
            return avail_name, url
    return None


TSDB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
TSDB_API = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"


def fetch_from_sportsdb(player_name: str) -> str | None:
    """Search TheSportsDB for a player, return cutout or thumb URL if found."""
    try:
        resp = requests.get(
            TSDB_API,
            params={"p": player_name},
            headers=TSDB_HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        players = data.get("player") or []
        if not players:
            return None
        # Prefer cricket players; pick first result
        cricket = [p for p in players if p.get("strSport", "").lower() == "cricket"]
        candidate = cricket[0] if cricket else players[0]
        # Only return cutout (PNG). Thumb images are JPG and not wanted.
        return candidate.get("strCutout") or None
    except Exception:
        return None


def download_image(url: str, save_path: Path, headers: dict | None = None) -> bool:
    h = headers if headers is not None else HEADERS
    try:
        resp = requests.get(url, headers=h, timeout=20)
        if resp.status_code == 200 and len(resp.content) > 500:
            save_path.write_bytes(resp.content)
            return True
        print(f"    ✗ HTTP {resp.status_code}")
        return False
    except Exception as exc:
        print(f"    ✗ Error: {exc}")
        return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("Perth Scorchers BBL Player Jersey Downloader")
    print("=" * 65)
    print(f"Fetching: {SOURCE_URL}\n")

    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    available = fetch_player_images(html)
    print(f"Players found on website: {len(available)}")
    for name in sorted(available):
        print(f"  • {name}")
    print()

    ok, skip, fail = 0, 0, 0
    not_found = []

    for player in REQUESTED_PLAYERS:
        filename = name_to_filename(player)
        save_path = OUTPUT_DIR / filename
        print(f"  {player}")

        match = best_match(player, available)
        if not match:
            print(f"    ✗ Not on official site — trying TheSportsDB...")
            tsdb_url = fetch_from_sportsdb(player)
            if tsdb_url:
                fb_path = OUTPUT_DIR / name_to_filename(player)  # always .png
                if download_image(tsdb_url, fb_path, headers=TSDB_HEADERS):
                    size = fb_path.stat().st_size
                    print(f"    ✓ TheSportsDB: {fb_path.name} ({size:,} bytes)")
                    ok += 1
                else:
                    print(f"    ✗ TheSportsDB download failed")
                    not_found.append(player)
                    fail += 1
            else:
                print(f"    ✗ Not found on TheSportsDB either")
                not_found.append(player)
                skip += 1
            time.sleep(0.3)
            continue

        matched_name, url = match
        if matched_name != player:
            print(f"    → matched as: {matched_name}")
        print(f"    → {filename}")

        if download_image(url, save_path):
            size = save_path.stat().st_size
            print(f"    ✓ Saved ({size:,} bytes)")
            ok += 1
        else:
            fail += 1

        time.sleep(0.3)

    print(f"\n{'=' * 65}")
    print(f"Done: {ok} downloaded, {fail} failed, {skip} not found anywhere")
    print(f"Saved to: {OUTPUT_DIR}")

    if not_found:
        print(f"\nPlayers not found anywhere ({len(not_found)}):")
        for p in not_found:
            print(f"  • {p}")


if __name__ == "__main__":
    main()
