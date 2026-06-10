"""
Melbourne Renegades BBL Player Image Downloader
Fetches player images from melbournerenegades.com.au
Falls back to TheSportsDB (PNG cutout), then Wikipedia (converted to PNG).
Saves as lowercase_underscore PNG filenames.
"""

import requests
import re
import io
import time
import urllib.request
from pathlib import Path
from PIL import Image

OUTPUT_DIR = Path("f:/logo/melbourne_renegades_players")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.melbournerenegades.com.au/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

TSDB_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
WIKI_HEADERS  = {"User-Agent": "CricketLogoResearch/1.0"}

SOURCE_URL = "https://www.melbournerenegades.com.au/players/bbl"
TSDB_API   = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"

# Official Renegades news/signing images (when not yet on /players/bbl)
RENEGADES_NEWS_IMAGES = {
    "Callum Stow": "https://resources.melbourne-renegades.pulselive.com/melbourne-renegades/photo/2025/10/06/72e1b610-d48c-4fe6-8769-c6c853b4a388/MR-2025-26-Player-Signings-Template-1920x1080_TEMP.jpg",
    "Scott Edwards": "https://resources.melbourne-renegades.pulselive.com/melbourne-renegades/photo/2024/01/12/04d341f0-fe25-4f9f-8c06-561e6d213156/MR-SE-signs-1920x1080.jpg",
    "Jordan Cox": "https://resources.melbourne-renegades.pulselive.com/melbourne-renegades/photo/2023/12/07/a0040341-6a12-4fa5-a1e0-906c89cd3536/jc_16x9.png",
    "Xavier Crone": "https://resources.melbourne-renegades.pulselive.com/melbourne-renegades/photo/2024/12/10/b8b09166-e5c8-4026-abd2-b2636fbab8df/MR_Crone-Harris_Signing_1920x1080.png",
}

# Other official BBL team sites (PulseLive body jersey PNGs)
BBL_SITES = [
    ("sydney-sixers", "https://www.sydneysixers.com.au/bbl-players"),
    ("adelaide-strikers", "https://www.adelaidestrikers.com.au/players"),
    ("hobart-hurricanes", "https://www.hobarthurricanes.com.au/players/bbl"),
    ("melbourne-stars", "https://www.melbournestars.com.au/players/bbl"),
    ("perth-scorchers", "https://www.perthscorchers.com.au/players/bbl-players"),
    ("brisbane-heat", "https://www.brisbaneheat.com.au/players/bbl"),
    ("sydney-thunder", "https://www.sydneythunder.com.au/players"),
]

REQUESTED_PLAYERS = [
    "Adam Zampa",
    "Ben McDermott",
    "Brendan Doggett",
    "Caleb Paul Jewell",
    "Callum Stow",
    "Fergus O'Neill",
    "Harry Dixon",
    "Hassan Khan",
    "Jacob Bethell",
    "Jake Fraser-McGurk",
    "Jonathan Wells",
    "Jordan Cox",
    "Josh Brown",
    "Kane Richardson",
    "Mackenzie Harvey",
    "Mohammad Rizwan",
    "Mujeeb Ur Rahman",
    "Oliver Peake",
    "Quinton de Kock",
    "Scott Edwards",
    "Tawanda Muyeye",
    "Tim Seifert",
    "Tom Rogers",
    "Will Sutherland",
    "Xavier Crone",
]


def name_to_filename(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "") + ".png"


def normalize(name: str) -> str:
    return re.sub(r"[^a-z ]", "", name.lower()).strip()


def first_name_match(a: str, b: str) -> bool:
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    variants = {"muhammad", "mohammad", "mohammed"}
    return a in variants and b in variants


def best_match(requested: str, available: dict[str, str]) -> tuple[str, str] | None:
    req_norm = normalize(requested)
    req_parts = req_norm.split()
    for avail_name, url in available.items():
        av_norm = normalize(avail_name)
        av_parts = av_norm.split()
        if req_norm == av_norm:
            return avail_name, url
        if len(req_parts) >= 2 and len(av_parts) >= 2:
            if req_parts[0] == av_parts[0] and req_parts[-1] == av_parts[-1]:
                return avail_name, url
            if req_parts[-1] == av_parts[-1] and (
                first_name_match(req_parts[0], av_parts[0])
            ):
                return avail_name, url
        req_words = [w for w in req_parts if len(w) > 1]
        av_words  = [w for w in av_parts  if len(w) > 1]
        if req_words == av_words:
            return avail_name, url
        # Muhammad/Mohammad spelling variant
        if len(req_words) >= 2 and len(av_words) >= 2:
            if req_words[-1] == av_words[-1] and first_name_match(req_words[0], av_words[0]):
                return avail_name, url
        # "Caleb Paul Jewell" <-> "CALEB JEWELL" — middle name
        if len(req_words) >= 2 and len(av_words) >= 2:
            if req_words[0] == av_words[0] and req_words[-1] == av_words[-1]:
                return avail_name, url
    return None


def fetch_player_images(html: str) -> dict[str, str]:
    players: dict[str, str] = {}
    pod_blocks = re.findall(
        r"o-person-pod__inner[^>]*href=[\"']?(/players/[^\"'\s>]+)[^>]*>(.*?)o-person-pod__name[^>]*>([^<]+)<",
        html, re.DOTALL,
    )
    for _href, block, name in pod_blocks:
        m = re.search(
            r'srcset="(https://resources\.melbourne-renegades\.pulselive\.com/photo-resources/[^?"]+)',
            block,
        )
        if not m:
            m = re.search(
                r'src="(https://resources\.melbourne-renegades\.pulselive\.com/photo-resources/[^?"]+)',
                block,
            )
        if m:
            players[name.strip()] = m.group(1) + "?width=560&height=668"
    return players


def fetch_bbl_site_images(cdn: str, url: str) -> dict[str, str]:
    headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Referer": url.rsplit("/", 2)[0] + "/",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return {}
        html = resp.text
    except Exception:
        return {}

    players: dict[str, str] = {}
    cdn_pat = cdn.replace("-", r"\-")
    pod_blocks = re.findall(
        r"o-person-pod__inner[^>]*href=[\"']?(/players/[^\"'\s>]+)[^>]*>(.*?)o-person-pod__name[^>]*>([^<]+)<",
        html, re.DOTALL,
    )
    for _href, block, name in pod_blocks:
        m = re.search(
            rf'srcset="(https://resources\.{cdn_pat}\.pulselive\.com/photo-resources/[^?"]+)',
            block,
        )
        if not m:
            m = re.search(
                rf'src="(https://resources\.{cdn_pat}\.pulselive\.com/photo-resources/[^?"]+)',
                block,
            )
        if m:
            players[name.strip()] = m.group(1) + "?width=560&height=668"
    return players


def fetch_from_sportsdb(player_name: str) -> str | None:
    try:
        resp = requests.get(TSDB_API, params={"p": player_name},
                            headers=TSDB_HEADERS, timeout=15)
        data = resp.json()
        players = data.get("player") or []
        if not players:
            return None
        cricket = [p for p in players if p.get("strSport", "").lower() == "cricket"]
        candidate = cricket[0] if cricket else players[0]
        return candidate.get("strCutout") or candidate.get("strThumb") or None
    except Exception:
        return None


def fetch_from_wikipedia(player_name: str) -> str | None:
    try:
        time.sleep(1)
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


def download_image(url: str, save_path: Path, use_urllib: bool = False,
                   headers: dict | None = None, convert_to_png: bool = False) -> bool:
    try:
        if use_urllib:
            opener = urllib.request.build_opener()
            opener.addheaders = [("User-Agent", "Mozilla/5.0 (compatible; Wikimedia/1.0)")]
            with opener.open(url, timeout=30) as r:
                data = r.read()
        else:
            h = headers or HEADERS
            resp = requests.get(url, headers=h, timeout=20)
            if resp.status_code != 200 or len(resp.content) < 500:
                print(f"    FAIL HTTP {resp.status_code}")
                return False
            data = resp.content

        if convert_to_png:
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img.save(save_path, "PNG")
        else:
            save_path.write_bytes(data)
        return True
    except Exception as exc:
        print(f"    FAIL Error: {exc}")
        return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("Melbourne Renegades BBL Player Image Downloader")
    print("=" * 65)
    print(f"Fetching: {SOURCE_URL}\n")

    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    available = fetch_player_images(resp.text)

    bbl_fallback: dict[str, tuple[str, str]] = {}
    for cdn, url in BBL_SITES:
        for name, img_url in fetch_bbl_site_images(cdn, url).items():
            bbl_fallback[name] = (cdn, img_url)
        time.sleep(0.3)

    print(f"Players found on website: {len(available)}")
    for name in sorted(available):
        print(f"  - {name}")
    print()

    ok = fail = skip = 0
    not_found = []

    for player in REQUESTED_PLAYERS:
        save_path = OUTPUT_DIR / name_to_filename(player)
        print(f"  {player}")

        # 1. Official site
        match = best_match(player, available)
        if match:
            matched_name, url = match
            if matched_name != player:
                print(f"    -> matched as: {matched_name}")
            print(f"    -> {save_path.name}")
            if download_image(url, save_path, headers=HEADERS):
                print(f"    OK Official site ({save_path.stat().st_size:,} bytes)")
                ok += 1
            else:
                fail += 1
            time.sleep(0.3)
            continue

        # 2. Renegades news/signing images
        news_url = RENEGADES_NEWS_IMAGES.get(player)
        if news_url:
            print(f"    -> {save_path.name}")
            needs_convert = not news_url.lower().endswith(".png")
            if download_image(news_url, save_path, headers=HEADERS, convert_to_png=needs_convert):
                print(f"    OK Renegades news ({save_path.stat().st_size:,} bytes)")
                ok += 1
                time.sleep(0.3)
                continue
            print(f"    FAIL Renegades news download failed")

        # 3. Other official BBL team sites
        bbl_urls = {name: url for name, (cdn, url) in bbl_fallback.items()}
        match = best_match(player, bbl_urls)
        if match:
            matched_name, img_url = match
            cdn = bbl_fallback[matched_name][0]
            if matched_name != player:
                print(f"    -> matched as: {matched_name} @ {cdn}")
            print(f"    -> {save_path.name}")
            site_url = next(u for c, u in BBL_SITES if c == cdn)
            img_headers = {**HEADERS, "Referer": site_url.rsplit("/", 2)[0] + "/"}
            if download_image(img_url, save_path, headers=img_headers):
                print(f"    OK BBL official ({cdn}) ({save_path.stat().st_size:,} bytes)")
                ok += 1
                time.sleep(0.3)
                continue
            print(f"    FAIL BBL official download failed")

        # 4. TheSportsDB (PNG cutout only)
        print(f"    Not on official site - trying TheSportsDB...")
        tsdb_url = fetch_from_sportsdb(player)
        if tsdb_url:
            if download_image(tsdb_url, save_path, headers=TSDB_HEADERS):
                print(f"    OK TheSportsDB ({save_path.stat().st_size:,} bytes)")
                ok += 1
                time.sleep(0.3)
                continue
            print(f"    FAIL TheSportsDB download failed")

        # 5. Wikipedia (convert JPG->PNG)
        print(f"    -> Trying Wikipedia...")
        wiki_url = fetch_from_wikipedia(player)
        if wiki_url:
            needs_convert = not wiki_url.lower().endswith(".png")
            if download_image(wiki_url, save_path, use_urllib=needs_convert,
                              convert_to_png=needs_convert, headers=WIKI_HEADERS):
                label = " (converted to PNG)" if needs_convert else ""
                print(f"    OK Wikipedia{label} ({save_path.stat().st_size:,} bytes)")
                ok += 1
            else:
                print(f"    FAIL Wikipedia download failed")
                not_found.append(player)
                fail += 1
        else:
            print(f"    FAIL Not found anywhere")
            not_found.append(player)
            skip += 1

        time.sleep(0.3)

    print(f"\n{'=' * 65}")
    print(f"Done: {ok} downloaded, {fail} failed, {skip} not found anywhere")
    print(f"Saved to: {OUTPUT_DIR}")

    if not_found:
        print(f"\nPlayers not found anywhere ({len(not_found)}):")
        for p in not_found:
            print(f"  - {p}")


if __name__ == "__main__":
    main()
