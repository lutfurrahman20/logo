"""
MLB Multi-Team Player Headshot Scraper
Fetches the 40-man roster from the MLB Stats API for each team, resolves ESPN
athlete IDs via ESPN search, and downloads headshots from the ESPN CDN
(with MLB CDN fallback). Each team is saved to its own output folder.
"""

import re
import time
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_SEARCH_API = "https://site.api.espn.com/apis/search/v2"
BASE_OUTPUT_DIR = Path("f:/logo")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# (team display name, MLB Stats API team ID, ESPN team ID, output folder name)
TEAMS = [
    ("Chicago White Sox",    145,  4, "chicago_white_sox_mlb_player_logos"),
    ("Cincinnati Reds",      113, 17, "cincinnati_reds_mlb_player_logos"),
    ("Cleveland Guardians",  114,  5, "cleveland_guardians_mlb_player_logos"),
    ("Colorado Rockies",     115, 27, "colorado_rockies_mlb_player_logos"),
    ("Detroit Tigers",       116,  6, "detroit_tigers_mlb_player_logos"),
    ("Houston Astros",       117, 18, "houston_astros_mlb_player_logos"),
    ("Kansas City Royals",   118,  7, "kansas_city_royals_mlb_player_logos"),
    ("Los Angeles Angels",   108,  3, "los_angeles_angels_mlb_player_logos"),
    ("Los Angeles Dodgers",  119, 19, "los_angeles_dodgers_mlb_player_logos"),
    ("Miami Marlins",        146, 28, "miami_marlins_mlb_player_logos"),
    ("Milwaukee Brewers",    158,  8, "milwaukee_brewers_mlb_player_logos"),
    ("Minnesota Twins",      142,  9, "minnesota_twins_mlb_player_logos"),
    ("New York Mets",        121, 21, "new_york_mets_mlb_player_logos"),
    ("New York Yankees",     147, 10, "new_york_yankees_mlb_player_logos"),
    ("Athletics",            133, 11, "athletics_mlb_player_logos"),
    ("Philadelphia Phillies",143, 22, "philadelphia_phillies_mlb_player_logos"),
    ("Pittsburgh Pirates",   134, 23, "pittsburgh_pirates_mlb_player_logos"),
    ("San Diego Padres",     135, 25, "san_diego_padres_mlb_player_logos"),
    ("San Francisco Giants", 137, 26, "san_francisco_giants_mlb_player_logos"),
    ("Seattle Mariners",     136, 12, "seattle_mariners_mlb_player_logos"),
    ("St. Louis Cardinals",  138, 24, "st_louis_cardinals_mlb_player_logos"),
    ("Tampa Bay Rays",       139, 30, "tampa_bay_rays_mlb_player_logos"),
    ("Texas Rangers",        140, 13, "texas_rangers_mlb_player_logos"),
    ("Toronto Blue Jays",    141, 14, "toronto_blue_jays_mlb_player_logos"),
    ("Washington Nationals", 120, 20, "washington_nationals_mlb_player_logos"),
]
# ───────────────────────────────────────────────────────────────────────────────


def safe_filename(name: str) -> str:
    """Remove characters invalid on Windows; keep spaces, dots, hyphens."""
    return re.sub(r'[\\/:*?"<>|]', "", name.strip())


def get_espn_active_roster(espn_team_id: int) -> dict:
    """Return {player_name: headshot_url} for the ESPN active roster."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/{espn_team_id}/roster"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
    except Exception as exc:
        print(f"  ESPN roster fetch error: {exc}")
        return {}


def get_mlb_40man_roster(mlb_team_id: int) -> list:
    """Return [{name, mlb_id}] for the full 40-man roster from MLB Stats API."""
    url = f"https://statsapi.mlb.com/api/v1/teams/{mlb_team_id}/roster/40Man"
    resp = requests.get(url, headers=HEADERS, timeout=15)
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


def process_team(team_name: str, mlb_id: int, espn_id: int, folder_name: str):
    output_dir = BASE_OUTPUT_DIR / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"  {team_name}")
    print(f"{'=' * 60}")
    print(f"  Output folder : {output_dir}")

    espn_roster = get_espn_active_roster(espn_id)
    print(f"  ESPN active roster : {len(espn_roster)} players")

    mlb_roster = get_mlb_40man_roster(mlb_id)
    print(f"  MLB 40-man roster  : {len(mlb_roster)} players")
    print()

    results = {"downloaded": 0, "skipped": 0, "no_image": 0}
    total = len(mlb_roster)

    for i, player in enumerate(mlb_roster, 1):
        name      = player["name"]
        player_id = player["mlb_id"]
        safe      = safe_filename(name)
        out_path  = output_dir / f"{safe}.png"

        print(f"  [{i:>3}/{total}] {name}")

        if out_path.exists() and out_path.stat().st_size > 1000:
            print("           Already exists - skipping")
            results["skipped"] += 1
            continue

        # Priority 1: ESPN active roster (URL already known)
        img_url = espn_roster.get(name, "")
        use_mlb = False

        # Priority 2: ESPN search API
        if not img_url:
            print("           Searching ESPN ...")
            img_url = espn_search_headshot(name)
            time.sleep(0.5)

        # Priority 3: MLB CDN fallback
        if not img_url and player_id:
            img_url = mlb_cdn_headshot(player_id)
            use_mlb = True

        if not img_url:
            print("           No image URL found")
            results["no_image"] += 1
            continue

        source = "MLB CDN" if use_mlb else "ESPN"
        print(f"           [{source}] {img_url}")

        if download_image(img_url, out_path):
            size_kb = out_path.stat().st_size / 1024
            print(f"           Saved ({size_kb:.1f} KB)")
            results["downloaded"] += 1
        else:
            if not use_mlb and player_id:
                fallback = mlb_cdn_headshot(player_id)
                print(f"           Fallback to MLB CDN: {fallback}")
                if download_image(fallback, out_path):
                    size_kb = out_path.stat().st_size / 1024
                    print(f"           Saved via MLB CDN ({size_kb:.1f} KB)")
                    results["downloaded"] += 1
                    time.sleep(0.3)
                    continue
            results["no_image"] += 1

        time.sleep(0.3)

    print(f"\n  SUMMARY - {team_name}")
    print(f"  Downloaded : {results['downloaded']}")
    print(f"  Skipped    : {results['skipped']}")
    print(f"  No image   : {results['no_image']}")
    return results


def main():
    print("=" * 60)
    print("  MLB Multi-Team Player Headshot Scraper")
    print(f"  Teams to process: {len(TEAMS)}")
    print("=" * 60)

    grand_total = {"downloaded": 0, "skipped": 0, "no_image": 0}

    for team_name, mlb_id, espn_id, folder_name in TEAMS:
        r = process_team(team_name, mlb_id, espn_id, folder_name)
        for k in grand_total:
            grand_total[k] += r[k]

    print(f"\n{'=' * 60}")
    print("  GRAND TOTAL SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Teams processed : {len(TEAMS)}")
    print(f"  Downloaded      : {grand_total['downloaded']}")
    print(f"  Skipped         : {grand_total['skipped']}")
    print(f"  No image        : {grand_total['no_image']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
