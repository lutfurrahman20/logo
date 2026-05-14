"""
ESPN Men's College Basketball Team Logo Downloader
Fetches team logos from ESPN CDN and saves with user-specified names.
"""

import requests
import time
from pathlib import Path

OUTPUT_DIR = Path("f:/logo/ncaab_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# User's desired save names (exact filenames without extension)
DESIRED_NAMES = [
    "Abilene Christian",
    "Air Force",
    "Akron",
    "Alabama",
    "Alabama A&M",
    "Alabama St",
    "Alabama State",
    "Alcorn State",
    "American University",
    "Appalachian State",
    "Arizona",
    "Arizona State",
    "Arkansas",
    "Arkansas Pine Bluff",
    "Arkansas State",
    "Army",
    "Auburn",
    "Austin Peay",
    "BYU",
    "Ball State",
    "Baylor",
    "Bellarmine",
    "Belmont",
    "Bethune Cookman",
    "Binghamton",
    "Boise State",
    "Boston College",
    "Boston University",
    "Bowling Green",
    "Bradley",
    "Brown",
    "Bryant",
    "Bucknell",
    "Buffalo",
    "Butler",
    "Cal Poly",
    "Cal State Bakersfield",
    "Cal State Fullerton",
    "Cal State Northridge",
    "California",
    "California Baptist",
    "Campbell",
    "Canisius",
    "Central Arkansas",
    "Central Connecticut",
    "Central Michigan",
    "Charleston",
    "Charleston Southern",
    "Charlotte",
    "Chattanooga",
    "Chicago State",
    "Cincinnati",
    "Clemson",
    "Cleveland State",
    "Coastal Carolina",
    "Colgate",
    "Colorado",
    "Colorado State",
    "Columbia",
    "Connecticut",
    "Coppin State",
    "Cornell",
    "Creighton",
    "Dartmouth",
    "Davidson",
    "Dayton",
    "DePaul",
    "Delaware",
    "Delaware State",
    "Denver",
    "Detroit Mercy",
    "Draft Picks",
    "Drake",
    "Drexel",
    "Duke",
    "Duquesne",
    "East Carolina",
    "East Tennessee State",
    "Eastern Illinois",
    "Eastern Kentucky",
    "Eastern Michigan",
    "Eastern Washington",
    "Elon",
    "Evansville",
    "Fairfield",
    "Fairleigh Dickinson",
    "Florida",
    "Florida A&M",
    "Florida Atlantic",
    "Florida Gulf Coast",
    "Florida International",
    "Florida State",
    "Fordham",
    "Fresno State",
    "Furman",
    "Gardner-Webb",
    "George Mason",
    "George Washington",
    "Georgetown",
    "Georgia",
    "Georgia Southern",
    "Gonzaga",
    "Harvard Crimson",
    "Houston",
    "Illinois",
    "Indiana",
    "Iowa",
    "Iowa State",
    "Kansas",
    "Kansas State",
    "Kentucky",
    "Louisville",
    "Marquette",
    "Maryland",
    "Massachusetts",
    "Miami",
    "Miami (OH)",
    "Michigan",
    "Michigan State",
    "Mississippi State",
    "Missouri",
    "NC State",
    "Nebraska",
    "North Carolina",
    "Northwestern",
    "Ohio State",
    "Ole Miss",
    "Oregon",
    "Penn Quakers",
    "Portland",
    "Providence",
    "Purdue",
    "Rutgers",
    "SMU",
    "Saint Louis Billikens",
    "South Carolina",
    "South Florida Bulls",
    "St. John's",
    "Tennessee",
    "Texas",
    "Texas A&M",
    "UCF",
    "UMBC Retrievers",
    "Vermont Catamounts",
    "Villanova",
    "Virginia",
    "Virginia Tech",
    "Wake Forest",
    "Washington",
    "West Virginia",
    "Western Michigan",
    "Wisconsin",
    "Yale Bulldogs",
]

# Maps user's desired save name → keyword to search in ESPN displayName / shortDisplayName.
# None = skip (not a real team).
OVERRIDES = {
    "Alabama":              "Alabama Crimson Tide",   # avoid matching Alabama A&M / State
    "Alabama St":           "Alabama State",           # intentional alias of Alabama State
    "Bethune Cookman":      "Bethune-Cookman",
    "Connecticut":          "UConn",                   # shortDisplayName = "UConn"
    "Draft Picks":          None,                      # not a real NCAA team — skip
    "Georgia":              "Georgia Bulldogs",        # avoid matching Georgia Southern/State/Tech
    "Harvard Crimson":      "Harvard Crimson",         # ESPN displayName is exact
    "Miami":                "Miami Hurricanes",        # University of Miami (FL)
    "Miami (OH)":           "Miami (OH)",              # Miami of Ohio Redhawks
    "NC State":             "NC State",                # ESPN shortDisplayName
    "Ole Miss":             "Ole Miss",
    "Penn Quakers":         "Pennsylvania",            # ESPN: "Pennsylvania Quakers"
    "Saint Louis Billikens": "Saint Louis",
    "South Carolina":       "South Carolina Gamecocks",
    "South Florida Bulls":  "South Florida",
    "UMBC Retrievers":      "UMBC",
    "Vermont Catamounts":   "Vermont",
    "Washington":           "Washington Huskies",      # avoid Washington State
    "Yale Bulldogs":        "Yale",
    "SMU":                  "SMU",
    "UCF":                  "UCF",
    "Appalachian State":    "App State",
    "Arkansas Pine Bluff":  "Arkansas-Pine Bluff",
}


def fetch_all_teams() -> dict:
    """Fetch all NCAAB teams from ESPN API, return dict of id → team info."""
    teams = {}
    page = 1
    while True:
        url = (
            "https://site.api.espn.com/apis/site/v2/sports/basketball/"
            f"mens-college-basketball/teams?limit=500&page={page}"
        )
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        # Dig into the nested structure
        raw_teams = (
            data
            .get("sports", [{}])[0]
            .get("leagues", [{}])[0]
            .get("teams", [])
        )
        if not raw_teams:
            raw_teams = data.get("teams", [])

        for item in raw_teams:
            team = item.get("team", item)
            tid = str(team.get("id", ""))
            if not tid:
                continue
            teams[tid] = {
                "id":               tid,
                "displayName":      team.get("displayName", ""),
                "shortDisplayName": team.get("shortDisplayName", ""),
                "nickname":         team.get("nickname", ""),
                "location":         team.get("location", ""),
            }

        total_pages = data.get("pageCount", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)

    return teams


def find_team_id(desired_name: str, all_teams: dict) -> str | None:
    """
    Resolve a user-desired name to an ESPN team ID.
    Returns None if the entry should be skipped or cannot be found.
    """
    # 1. Check override table
    if desired_name in OVERRIDES:
        search = OVERRIDES[desired_name]
        if search is None:
            return None   # explicitly skip
    else:
        search = desired_name

    sl = search.lower()

    # 2. Exact match on displayName
    for tid, t in all_teams.items():
        if t["displayName"].lower() == sl:
            return tid

    # 3. Exact match on shortDisplayName
    for tid, t in all_teams.items():
        if t["shortDisplayName"].lower() == sl:
            return tid

    # 4. displayName starts with the search string (word boundary)
    for tid, t in all_teams.items():
        dn = t["displayName"].lower()
        if dn.startswith(sl + " ") or dn == sl:
            return tid

    # 5. search string contained in displayName
    for tid, t in all_teams.items():
        if sl in t["displayName"].lower():
            return tid

    # 6. location exact match
    for tid, t in all_teams.items():
        if t["location"].lower() == sl:
            return tid

    return None  # not found


def download_logo(team_id: str, save_path: Path) -> bool:
    """Download a team logo PNG from ESPN CDN."""
    url = f"https://a.espncdn.com/i/teamlogos/ncaa/500/{team_id}.png"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 500:
            save_path.write_bytes(r.content)
            return True
        print(f"    WARNING HTTP {r.status_code} or empty response")
    except Exception as exc:
        print(f"    ERROR {exc}")
    return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  ESPN NCAAB Team Logo Downloader")
    print("=" * 65)
    print(f"  Fetching team list from ESPN API ...")

    all_teams = fetch_all_teams()
    print(f"  Found {len(all_teams)} teams\n")

    success, failed, skipped = 0, [], []

    for desired_name in DESIRED_NAMES:
        # Skip check via override
        if OVERRIDES.get(desired_name) is None and desired_name in OVERRIDES:
            print(f"  SKIP   {desired_name!r}  (not a real NCAA team)")
            skipped.append(desired_name)
            continue

        team_id = find_team_id(desired_name, all_teams)

        if team_id is None:
            print(f"  MISS   {desired_name!r}  — no ESPN match found")
            failed.append(desired_name)
            continue

        team_info = all_teams[team_id]
        save_path = OUTPUT_DIR / f"{desired_name}.png"

        ok = download_logo(team_id, save_path)
        if ok:
            print(
                f"  OK     {desired_name!r:<35} "
                f"← {team_info['displayName']}  (id={team_id})"
            )
            success += 1
        else:
            print(f"  FAIL   {desired_name!r}")
            failed.append(desired_name)

        time.sleep(0.08)   # be polite to ESPN CDN

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'=' * 65}")
    print(f"  Done!  Saved: {success}  Failed: {len(failed)}  Skipped: {len(skipped)}")
    print(f"  Output folder: {OUTPUT_DIR}")
    if skipped:
        print(f"\n  Skipped (not real teams): {skipped}")
    if failed:
        print(f"\n  Failed (no match / download error):")
        for name in failed:
            print(f"    - {name}")


if __name__ == "__main__":
    main()
