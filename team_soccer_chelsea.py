"""
Chelsea FC — Player Headshot Downloader (Soccer / EPL)

Downloads headshots for a specific list of Chelsea players.

Sources (tried in order per player):
  1. CFC Official — img.chelseafc.com (Cloudinary) photos scraped from signing/player
                    news articles on chelseafc.com.  Used for new 2025-26 signings
                    whose FPL photos are still in their previous club's kit, and for
                    academy / fringe players with no FPL photo at all.
  2. FPL CDN      — resources.premierleague.com/110x140 (current-season kit photos)
                    via Fantasy Premier League bootstrap API (team 7).
  3. ESPN CDN     — espncdn.com headshots via the ESPN soccer roster API (team 363).
                    Very sparse for Chelsea — only used as last resort.

NOTE: Alejandro Garnacho (Man Utd → CFC) and Liam Delap (Ipswich → CFC) are
      confirmed to have wrong-club kits in the FPL CDN.  Neither is allowed to
      fall back to FPL; CFC official photos are used instead.
NOTE: The legacy S3 CDN (platform-static-files.s3.amazonaws.com) is intentionally
      NOT used — it serves outdated photos of players in previous clubs' kits.

Squad verified against:
  https://www.espn.com/soccer/team/squad/_/id/363/chelsea
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/363/roster"
)
ESPN_HEADSHOT   = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

FPL_API         = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_CDN         = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{code}.png"
CHELSEA_FPL_ID  = 7

CFC_ARTICLE_BASE = "https://www.chelseafc.com/en/news/article/"
CFC_IMG_BASE     = "https://img.chelseafc.com/image/upload/"

OUTPUT_DIR = Path("f:/logo/chelsea_soccer_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
# ── Target Players ─────────────────────────────────────────────────────────────
TARGET_PLAYERS = [
    "Alejandro Garnacho",
    "Andrey Nascimento dos Santos",
    "Axel Disasi",
    "Benoît Badiashile",
    "Cole Palmer",
    "Dário Cassia Luís Essugo",
    "Enzo Fernández",
    "Estêvão Willian Almeida de Oliveira Gonçalves",
    "Facundo Buonanotte",
    "Filip Jørgensen",
    "Gabriel Slonina",
    "Jamie Gittens",
    "Jorrel Hato",
    "Josh Acheampong",
    "João Pedro Junqueira de Jesus",
    "Landon Emenalo",
    "Levi Colwill",
    "Liam Delap",
    "Malo Gusto",
    "Marc Cucurella",
    "Marc Guiu",
    "Max Merrick",
    "Moisés Caicedo",
    "Mykhailo Mudryk",
    "Ollie Harrison",
    "Pedro Lomba Neto",
    "Raheem Sterling",
    "Reece James",
    "Reggie Walsh",
    "Robert Sánchez",
    "Roméo Lavia",
    "Ryan Kavuma-McQueen",
    "Shumaira Mheuka",
    "Tosin Adarabioyo",
    "Trevoh Chalobah",
    "Tyrique George",
    "Wesley Fofana",
]

# Maps user's full legal name → ESPN display name where they differ
ESPN_NAME_OVERRIDES = {
    "Gabriel Slonina":                               "Gaga Slonina",
    "Shumaira Mheuka":                               "Shim Mheuka",
    "Andrey Nascimento dos Santos":                  "Andrey Santos",
    "Dário Cassia Luís Essugo":                      "Dário Essugo",
    "Roméo Lavia":                                   "Romeo Lavia",
    "Estêvão Willian Almeida de Oliveira Gonçalves": "Estêvão",
    "João Pedro Junqueira de Jesus":                 "João Pedro",
    "Pedro Lomba Neto":                              "Pedro Neto",
    "Ryan Kavuma-McQueen":                           "Ryan Kavuma-Mcqueen",
}

# ── CFC Article Slugs ──────────────────────────────────────────────────────────
# Player name → article slug on www.chelseafc.com/en/news/article/
# Used for:
#   (a) New 2025-26 signings whose FPL CDN photos still show their previous club's kit
#   (b) Players with no FPL CDN photo (code returns 403)
#   (c) Players not (yet) in ESPN's Chelsea squad list
CFC_ARTICLE_SLUGS = {
    # ── Summer 2025 signings (wrong FPL kit confirmed or no FPL photo) ──────
    "Alejandro Garnacho":                            "chelsea-complete-alejandro-garnacho-signing",
    "Liam Delap":                                    "liam-delap-completes-chelsea-transfer",
    "Jamie Gittens":                                 "jamie-gittens-signs-for-chelsea",
    "Jorrel Hato":                                   "jorrel-hato-joins-chelsea",
    "Estêvão Willian Almeida de Oliveira Gonçalves": "estevao-arrives-at-chelsea",
    "Facundo Buonanotte":                            "facundo-buonanotte-completes-chelsea-loan-switch",
    "João Pedro Junqueira de Jesus":                 "joao-pedro-chelsea-squad-number-confirmed",
    # ── No FPL photo (403 / not registered in PL CDN yet) ───────────────────
    "Andrey Nascimento dos Santos":                  "young-brazilian-midfielder-santos-joins-chelsea",
    "Dário Cassia Luís Essugo":                      "everything-you-need-to-know-about-dario-essugo",
    "Landon Emenalo":                                "landon-emenalo-wants-to-begin-the-year-with-confidence",
    "Max Merrick":                                   "max-merrick-pens-new-contract",
    "Ryan Kavuma-McQueen":                           "who-is-ryan-kavuma-mcqueen-chelsea-winger",
    "Shumaira Mheuka":                               "teenage-kicks-shumaira-mheuka",
    # ── Players not listed in ESPN's squad (sold / loaned out / academy) ───
    "Axel Disasi":                                   "disasi-completes-chelsea-move",
    "Tyrique George":                                "tyrique-george-signs-new-chelsea-contract",
    "Raheem Sterling":                               "sterling-chelseas-intent-and-actions-convinced-me-to-sign",
    # ── Signed but previously missing (name mismatch or missing slug) ──────
    "Filip Jørgensen":                               "chelsea-complete-signing-of-filip-jorgensen",
    "Reggie Walsh":                                  "reggie-walsh-signs-new-contract",
}

# Players confirmed to have WRONG CLUB KIT in FPL CDN — never fall back to FPL
SKIP_FPL = {"Alejandro Garnacho", "Liam Delap"}

# For these players the article's /restricted/ images belong to OTHER players;
# use /editorial/ instead.
CFC_PREFER_EDITORIAL = {"Reggie Walsh"}

# URL path fragments that indicate the image is NOT a player headshot
CFC_IMG_SKIP = [
    "badge", "logo", "sponsor", "merch", "stadium", "retro",
    "shop", "pensioners", "broadcaster", "marketing",
    "app_sote", "cfcw", "google-play",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Lower-case, strip accents, collapse whitespace."""
    nfkd   = unicodedata.normalize("NFKD", s)
    ascii_ = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_).strip().lower()


_CHAR_MAP = str.maketrans({
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "TH",
    "ß": "ss",
    "ł": "l", "Ł": "L",
})


def safe_filename(name: str) -> str:
    """Return lower-case underscore filename (no accents, no special chars)."""
    name = name.strip().translate(_CHAR_MAP)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower()


def download_image(url: str, filepath: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 5000:
            filepath.write_bytes(r.content)
            return True
    except Exception as e:
        print(f"    ERROR    {e}")
    return False


def _squad_match(key: str, roster: dict) -> str | None:
    """
    Fuzzy-match normalized name against roster keys.
    Accepts: exact match, OR 2+ shared words, OR same last word + 1 shared word.
    """
    if key in roster:
        return key
    words    = key.split()
    last     = words[-1]
    word_set = set(words)
    for rk in roster:
        rw     = rk.split()
        common = word_set & set(rw)
        if len(common) >= 2:
            return rk
        if rw[-1] == last and len(common) >= 1:
            return rk
    return None


# ── Data-source builders ───────────────────────────────────────────────────────

def build_cfc_lookup() -> dict:
    """
    For each player in CFC_ARTICLE_SLUGS, fetches the chelseafc.com article and
    extracts the first qualifying player photo URL.

    Priority within each article:
      1. Images under /restricted/ (exclusive club-media signing/squad shots)
         — prefer .png (cutout headshots) over .jpg
      2. Images under /editorial/ (news / academy / match photos)
    Returns {player_name: full_image_url}.
    """
    lookup: dict = {}
    for player, slug in CFC_ARTICLE_SLUGS.items():
        url = CFC_ARTICLE_BASE + slug
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"    CFC article {slug}: HTTP {r.status_code}")
                continue

            raw_paths = re.findall(
                r'img\.chelseafc\.com/image/upload/([^\s"&\\]+)', r.text
            )

            filtered = []
            for p in raw_paths:
                low = p.lower()
                # Skip non-player images
                if any(tok in low for tok in CFC_IMG_SKIP):
                    continue
                filtered.append(p)

            if not filtered:
                print(f"    CFC article {slug}: no player images found")
                continue

            # Prefer restricted/ (exclusive Chelsea media)
            restricted = [p for p in filtered if "/restricted/" in p]
            editorial  = [p for p in filtered if "/editorial/" in p]

            # Some articles embed other players' restricted shots; use editorial
            if player in CFC_PREFER_EDITORIAL:
                category = editorial or restricted or filtered
            else:
                category = restricted or editorial or filtered

            # Within category prefer .png (cutout headshots) over .jpg
            pngs = [p for p in category if p.lower().endswith(".png")]
            chosen = (pngs or category)[0]

            lookup[player] = CFC_IMG_BASE + chosen
            time.sleep(0.3)  # be polite to chelseafc.com

        except Exception as e:
            print(f"    CFC article {slug}: {e}")

    return lookup


def build_espn_lookup() -> dict:
    """Returns {normalized_name: espn_player_id} for Chelsea's ESPN roster."""
    lookup: dict = {}
    try:
        print("  Fetching ESPN roster (team 363 / eng.1) ...")
        r = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for athlete in r.json().get("athletes", []):
            pid = str(athlete.get("id", ""))
            for n in (athlete.get("fullName", ""), athlete.get("displayName", "")):
                if n and pid:
                    lookup[normalize(n)] = pid
    except Exception as e:
        print(f"  WARNING  ESPN roster fetch failed: {e}")
    return lookup


def build_fpl_lookup() -> dict:
    """
    Returns {normalized_name: fpl_photo_url} for every Chelsea player in FPL.
    Uses resources.premierleague.com/110x140 which has current-season kit photos.
    """
    lookup: dict = {}
    try:
        print("  Fetching Fantasy Premier League bootstrap ...")
        r = requests.get(FPL_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for p in r.json().get("elements", []):
            if p.get("team") != CHELSEA_FPL_ID:
                continue
            code  = p.get("code", "")
            first = p.get("first_name", "")
            last  = p.get("second_name", "")
            full  = f"{first} {last}".strip()
            if full and code:
                lookup[normalize(full)] = FPL_CDN.format(code=code)
    except Exception as e:
        print(f"  WARNING  FPL fetch failed: {e}")
    return lookup


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  Chelsea FC — Player Headshot Scraper")
    print("=" * 60)
    print(f"  Players to download : {len(TARGET_PLAYERS)}")
    print(f"  Output folder       : {OUTPUT_DIR}\n")

    print("  Building CFC official article lookup ...")
    cfc_lookup  = build_cfc_lookup()
    espn_lookup = build_espn_lookup()
    fpl_lookup  = build_fpl_lookup()

    print(f"\n  CFC official entries: {len(cfc_lookup)}")
    print(f"  ESPN roster entries : {len(espn_lookup)}")
    print(f"  FPL roster entries  : {len(fpl_lookup)}\n")
    print("-" * 60)
    print("Downloading headshots ...\n")

    results = {"downloaded": 0, "skipped": 0, "no_image": 0}
    total   = len(TARGET_PLAYERS)

    for i, player_name in enumerate(TARGET_PLAYERS, 1):
        fname = safe_filename(player_name) + ".png"
        fpath = OUTPUT_DIR / fname

        print(f"  [{i:>2}/{total}] {player_name}")

        if fpath.exists():
            print(f"           Already exists — skipped")
            results["skipped"] += 1
            continue

        img_url: str | None = None

        # ── 1. CFC Official (for new signings / no-FPL players) ───────────
        cfc_url = cfc_lookup.get(player_name)
        if cfc_url:
            try:
                r = requests.get(cfc_url, headers=HEADERS, timeout=20)
                if r.status_code == 200 and len(r.content) > 5000:
                    img_url = cfc_url
            except Exception:
                pass

        # ── 2. FPL CDN (skip for players confirmed to have wrong-kit photos) ──
        if not img_url and player_name not in SKIP_FPL:
            search_keys = {normalize(player_name)}
            override = ESPN_NAME_OVERRIDES.get(player_name)
            if override:
                search_keys.add(normalize(override))

            for key in search_keys:
                matched = _squad_match(key, fpl_lookup)
                if matched:
                    fpl_url = fpl_lookup[matched]
                    try:
                        r = requests.get(fpl_url, headers=HEADERS, timeout=15)
                        if r.status_code == 200 and len(r.content) > 5000:
                            img_url = fpl_url
                            break
                    except Exception:
                        pass

        # ── 3. ESPN CDN (last resort — very sparse for Chelsea) ────────────
        if not img_url:
            espn_keys = {normalize(player_name)}
            override = ESPN_NAME_OVERRIDES.get(player_name)
            if override:
                espn_keys.add(normalize(override))

            for key in espn_keys:
                matched = _squad_match(key, espn_lookup)
                if matched:
                    espn_id  = espn_lookup[matched]
                    espn_url = ESPN_HEADSHOT.format(id=espn_id)
                    try:
                        r = requests.get(espn_url, headers=HEADERS, timeout=15)
                        if r.status_code == 200 and len(r.content) > 5000:
                            img_url = espn_url
                            break
                    except Exception:
                        pass

        # ── Save ──────────────────────────────────────────────────────────
        if img_url:
            ok = download_image(img_url, fpath)
            if ok:
                source = (
                    "CFC"  if "chelseafc" in img_url else
                    "ESPN" if "espncdn"   in img_url else
                    "FPL"
                )
                print(f"           [{source}] Saved → {fname}")
                results["downloaded"] += 1
            else:
                print(f"           Download failed")
                results["no_image"] += 1
        else:
            print(f"           No image found in any source")
            results["no_image"] += 1

        time.sleep(0.2)

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Downloaded  : {results['downloaded']}")
    print(f"  Skipped     : {results['skipped']}")
    print(f"  No image    : {results['no_image']}")
    print(f"  Output      : {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
