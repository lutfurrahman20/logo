"""
BBL Missing Players - Comprehensive Image Downloader
Checks all 8 BBL official team sites + TheSportsDB (PNG cutout only)
for players that were not found on their own team's website.
"""

import requests
import re
import time
import io
from pathlib import Path
from PIL import Image

TSDB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
TSDB_API = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"

# All 8 BBL team sites with their PulseLive CDN subdomain
BBL_SITES = [
    ("Perth Scorchers",       "https://www.perthscorchers.com.au/players/bbl-players",  "perth-scorchers"),
    ("Sydney Sixers",         "https://www.sydneysixers.com.au/bbl-players",             "sydney-sixers"),
    ("Brisbane Heat",         "https://www.brisbaneheat.com.au/players/bbl",             "brisbane-heat"),
    ("Hobart Hurricanes",     "https://www.hobarthurricanes.com.au/players/bbl",         "hobart-hurricanes"),
    ("Melbourne Renegades",   "https://www.melbournerenegades.com.au/players/bbl",       "melbourne-renegades"),
    ("Melbourne Stars",       "https://www.melbournestars.com.au/players/bbl",           "melbourne-stars"),
    ("Adelaide Strikers",     "https://www.adelaidestrikers.com.au/players",             "adelaide-strikers"),
    ("Sydney Thunder",        "https://www.sydneythunder.com.au/players",                "sydney-thunder"),
]

# Missing players: (save_dir, player_name)
MISSING = [
    # Perth Scorchers missing
    (Path("f:/logo/perth_scorchers_players"),    "Corey Rocchiccioli"),
    (Path("f:/logo/perth_scorchers_players"),    "Matthew Spoors"),
    (Path("f:/logo/perth_scorchers_players"),    "Keaton Jennings"),
    (Path("f:/logo/perth_scorchers_players"),    "Matthew Hurst"),
    (Path("f:/logo/perth_scorchers_players"),    "Zak Crawley"),
    # Sydney Sixers missing
    (Path("f:/logo/sydney_sixers_players"),      "Akeal Hosein"),
    (Path("f:/logo/sydney_sixers_players"),      "Hanno Jacobs"),
    (Path("f:/logo/sydney_sixers_players"),      "Izharulhaq Naveed"),
    (Path("f:/logo/sydney_sixers_players"),      "Lachlan Hearne"),
    (Path("f:/logo/sydney_sixers_players"),      "Rehan Ahmed"),
    (Path("f:/logo/sydney_sixers_players"),      "Ryan Hadley"),
    # Brisbane Heat missing
    (Path("f:/logo/brisbane_heat_players"),      "Daniel Drew"),
    (Path("f:/logo/brisbane_heat_players"),      "Paul Ian Walter"),
    (Path("f:/logo/brisbane_heat_players"),      "Tom Straker"),
    (Path("f:/logo/brisbane_heat_players"),      "Tom Whitney"),
    # Hobart Hurricanes missing
    (Path("f:/logo/hobart_hurricanes_players"),  "Bhanuka Rajapaksa"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Charlie Wakim"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Liam Guthrie"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Marcus Bean"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Mohammad Nawaz"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Nikhil Chaudhary"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Odean Smith"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Rishad Hossain"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Sahibzada Farhan"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Shai Hope"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Tim Ward"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Waqar Salamkheil"),
    (Path("f:/logo/hobart_hurricanes_players"),  "Will Prestwidge"),
]


def normalize(name: str) -> str:
    return re.sub(r"[^a-z ]", "", name.lower()).strip()


def name_to_filename(name: str) -> str:
    return name.lower().replace(" ", "_") + ".png"


def best_match(requested: str, available: dict[str, str]) -> tuple[str, str] | None:
    req_norm = normalize(requested)
    req_parts = req_norm.split()
    for avail_name, url in available.items():
        av_norm = normalize(avail_name)
        av_parts = av_norm.split()
        if req_norm == av_norm:
            return avail_name, url
        if len(req_parts) >= 2 and len(av_parts) >= 2:
            # First + last match (handles middle initial / extra words)
            if req_parts[0] == av_parts[0] and req_parts[-1] == av_parts[-1]:
                return avail_name, url
            # First name prefix match (Matt/Matthew, Mitch/Mitchell, etc.)
            if req_parts[-1] == av_parts[-1] and (
                req_parts[0].startswith(av_parts[0])
                or av_parts[0].startswith(req_parts[0])
            ):
                return avail_name, url
        # Remove middle initials and compare
        req_words = [w for w in req_parts if len(w) > 1]
        av_words = [w for w in av_parts if len(w) > 1]
        if req_words == av_words:
            return avail_name, url
        # Same first + last with extra middle words
        if len(req_words) >= 2 and len(av_words) >= 2:
            if req_words[0] == av_words[0] and req_words[-1] == av_words[-1]:
                return avail_name, url
    return None


def fetch_site_images(url: str, cdn_subdomain: str, referer: str) -> dict[str, str]:
    """Fetch all player images from a BBL team website."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": referer,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return {}
        html = resp.text
    except Exception:
        return {}

    players: dict[str, str] = {}
    cdn_pattern = cdn_subdomain.replace("-", r"\-")
    pod_blocks = re.findall(
        r"o-person-pod__inner[^>]*title='([^']+)'(.*?)o-person-pod__name",
        html, re.DOTALL,
    )
    for name, block in pod_blocks:
        m = re.search(
            rf'srcset="(https://resources\.{cdn_pattern}\.pulselive\.com/photo-resources/[^?"]+)',
            block,
        )
        if not m:
            m = re.search(
                rf'src="(https://resources\.{cdn_pattern}\.pulselive\.com/photo-resources/[^?"]+)',
                block,
            )
        if m:
            players[name.strip()] = m.group(1) + "?width=560&height=668"
    return players


WIKI_HEADERS = {
    "User-Agent": "CricketImageBot/1.0 (research)"
}


def fetch_from_sportsdb(player_name: str) -> str | None:
    """Return PNG cutout URL from TheSportsDB, or None."""
    try:
        resp = requests.get(TSDB_API, params={"p": player_name},
                            headers=TSDB_HEADERS, timeout=15)
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


def fetch_from_wikipedia(player_name: str) -> str | None:
    """Return a thumbnail image URL from Wikipedia for a player, or None."""
    try:
        time.sleep(0.8)  # Be polite to Wikipedia
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search",
                    "srsearch": player_name + " cricketer",
                    "srlimit": 1, "format": "json"},
            headers=WIKI_HEADERS, timeout=15,
        )
        results = resp.json().get("query", {}).get("search", [])
        if not results:
            return None
        title = results[0]["title"]
        # Guard against disambiguation pages matching wrong subjects
        if any(x in title.lower() for x in ["disambiguation", "list of"]):
            return None
        time.sleep(0.5)
        r2 = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "titles": title,
                    "prop": "pageimages", "pithumbsize": 600, "format": "json"},
            headers=WIKI_HEADERS, timeout=15,
        )
        pages = r2.json().get("query", {}).get("pages", {})
        for p in pages.values():
            thumb = p.get("thumbnail", {}).get("source", "")
            if thumb:
                return thumb
    except Exception:
        pass
    return None


def download_image(url: str, save_path: Path, headers: dict | None = None,
                   convert_to_png: bool = False) -> bool:
    h = headers or TSDB_HEADERS
    try:
        resp = requests.get(url, headers=h, timeout=20)
        if resp.status_code == 200 and len(resp.content) > 500:
            if convert_to_png:
                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                img.save(save_path, "PNG")
            else:
                save_path.write_bytes(resp.content)
            return True
        print(f"      ✗ HTTP {resp.status_code}")
        return False
    except Exception as exc:
        print(f"      ✗ Error: {exc}")
        return False


def main():
    print("=" * 65)
    print("BBL Missing Players — Comprehensive Image Downloader")
    print("=" * 65)

    # Pre-fetch all 8 BBL team sites once
    print("\nPre-fetching all 8 BBL team sites...")
    site_data: list[tuple[str, dict[str, str]]] = []
    for team_name, url, cdn in BBL_SITES:
        referer = url.rsplit("/", 2)[0] + "/"
        images = fetch_site_images(url, cdn, referer)
        print(f"  {team_name}: {len(images)} players found")
        site_data.append((team_name, images))
        time.sleep(0.5)

    print()
    ok = fail = skip = 0
    still_missing = []

    for save_dir, player in MISSING:
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / name_to_filename(player)

        # Skip if already downloaded
        if save_path.exists():
            print(f"  ✓ Already exists: {player}")
            ok += 1
            continue

        print(f"  {player}  [{save_dir.name}]")

        # Check all BBL sites
        found = False
        for team_name, images in site_data:
            match = best_match(player, images)
            if match:
                matched_name, url = match
                img_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www." + team_name.lower().replace(" ", "") + ".com.au/",
                }
                if download_image(url, save_path, headers=img_headers):
                    label = f" (matched as: {matched_name})" if matched_name != player else ""
                    size = save_path.stat().st_size
                    print(f"    ✓ {team_name}{label} ({size:,} bytes)")
                    ok += 1
                    found = True
                    break
                else:
                    print(f"    ✗ {team_name} download failed")

        if found:
            time.sleep(0.3)
            continue

        # Fallback 1: TheSportsDB (PNG cutout only)
        print(f"    → Not on any BBL site — trying TheSportsDB...")
        tsdb_url = fetch_from_sportsdb(player)
        if tsdb_url:
            if download_image(tsdb_url, save_path):
                size = save_path.stat().st_size
                print(f"    ✓ TheSportsDB ({size:,} bytes)")
                ok += 1
                time.sleep(0.3)
                continue
            else:
                print(f"    ✗ TheSportsDB download failed")

        # Fallback 2: Wikipedia (convert JPG→PNG)
        print(f"    → Trying Wikipedia...")
        wiki_url = fetch_from_wikipedia(player)
        if wiki_url:
            needs_convert = not wiki_url.lower().endswith(".png")
            if download_image(wiki_url, save_path, headers=WIKI_HEADERS,
                              convert_to_png=needs_convert):
                size = save_path.stat().st_size
                label = " (converted to PNG)" if needs_convert else ""
                print(f"    ✓ Wikipedia{label} ({size:,} bytes)")
                ok += 1
            else:
                print(f"    ✗ Wikipedia download failed")
                still_missing.append((save_dir.name, player))
                fail += 1
        else:
            print(f"    ✗ Not found anywhere")
            still_missing.append((save_dir.name, player))
            skip += 1

        time.sleep(0.3)

    print(f"\n{'=' * 65}")
    print(f"Done: {ok} downloaded/existing, {fail} failed, {skip} not found")

    if still_missing:
        print(f"\nStill not found anywhere ({len(still_missing)}):")
        for folder, p in still_missing:
            print(f"  • {p}  [{folder}]")


if __name__ == "__main__":
    main()
