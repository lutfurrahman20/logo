"""
Hobart Hurricanes BBL Player Image Downloader
Fetches player images from hobarthurricanes.com.au
Falls back to TheSportsDB (PNG cutout only) for players not on the official site.
Saves as lowercase_underscore PNG filenames.
"""

import requests
import re
import time
from pathlib import Path

OUTPUT_DIR = Path("f:/logo/hobart_hurricanes_players")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.hobarthurricanes.com.au/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TSDB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

SOURCE_URL = "https://www.hobarthurricanes.com.au/players/bbl"
TSDB_API = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"

REQUESTED_PLAYERS = [
    "Bhanuka Rajapaksa",
    "Billy Stanlake",
    "Charlie Wakim",
    "Chris Jordan",
    "Iain Carlisle",
    "Jake Doran",
    "Jake Weatherald",
    "Liam Guthrie",
    "Mac Wright",
    "Marcus Bean",
    "Matthew Wade",
    "Mitchell J Owen",
    "Mohammad Nabi",
    "Mohammad Nawaz",
    "Nathan Ellis",
    "Nikhil Chaudhary",
    "Odean Smith",
    "Patrick Dooley",
    "Peter Hatzoglou",
    "Riley Meredith",
    "Rishad Hossain",
    "Sahibzada Farhan",
    "Sam Hain",
    "Shai Hope",
    "Tim David",
    "Tim Ward",
    "Waqar Salamkheil",
    "Will Prestwidge",
]


def name_to_filename(name: str) -> str:
    return name.lower().replace(" ", "_") + ".png"


def normalize(name: str) -> str:
    return re.sub(r"[^a-z ]", "", name.lower()).strip()


def fetch_player_images(html: str) -> dict[str, str]:
    players: dict[str, str] = {}

    def with_size(url: str) -> str:
        return url + "?width=560&height=668"

    pod_blocks = re.findall(
        r"o-person-pod__inner[^>]*title='([^']+)'(.*?)o-person-pod__name",
        html,
        re.DOTALL,
    )
    for name, block in pod_blocks:
        m = re.search(
            r'srcset="(https://resources\.hobart-hurricanes\.pulselive\.com/photo-resources/[^?"]+)',
            block,
        )
        if not m:
            m = re.search(
                r'src="(https://resources\.hobart-hurricanes\.pulselive\.com/photo-resources/[^?"]+)',
                block,
            )
        if m:
            players[name.strip()] = with_size(m.group(1))

    return players


def best_match(requested: str, available: dict[str, str]) -> tuple[str, str] | None:
    req_norm = normalize(requested)
    for avail_name, url in available.items():
        av_norm = normalize(avail_name)
        if req_norm == av_norm:
            return avail_name, url
        req_parts = req_norm.split()
        av_parts = av_norm.split()
        if len(req_parts) >= 2 and len(av_parts) >= 2:
            # First + last match (handles middle initial: "Mitchell J Owen" ↔ "MITCHELL OWEN")
            if req_parts[0] == av_parts[0] and req_parts[-1] == av_parts[-1]:
                return avail_name, url
            # First name prefix (Matt/Matthew, Paddy/Patrick)
            if req_parts[-1] == av_parts[-1] and (
                req_parts[0].startswith(av_parts[0])
                or av_parts[0].startswith(req_parts[0])
            ):
                return avail_name, url
        # "Patrick Dooley" ↔ "Paddy Dooley"
        req_words = [w for w in req_parts if len(w) > 1]
        av_words = [w for w in av_parts if len(w) > 1]
        if req_words[-1:] == av_words[-1:] and len(req_words) == len(av_words):
            # Last name matches, check first name starts with same letter
            if req_words[0][0] == av_words[0][0]:
                return avail_name, url
    return None


def fetch_from_sportsdb(player_name: str) -> str | None:
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
        cricket = [p for p in players if p.get("strSport", "").lower() == "cricket"]
        candidate = cricket[0] if cricket else players[0]
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
    print("Hobart Hurricanes BBL Player Image Downloader")
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
                fb_path = OUTPUT_DIR / name_to_filename(player)
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
