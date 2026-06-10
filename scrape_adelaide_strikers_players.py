"""
Adelaide Strikers BBL (Men's) Player Image Downloader
Fetches official body-jersey images from adelaidestrikers.com.au/players
Skips WBBL / women's players on the combined squad page.
"""

import re
import time
from pathlib import Path

import requests

OUTPUT_DIR = Path("f:/logo/adelaide_strikers_players")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.adelaidestrikers.com.au/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

SOURCE_URL = "https://www.adelaidestrikers.com.au/players"
CDN = "adelaide-strikers"


def name_to_filename(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "") + ".png"


def fetch_player_pods(html: str) -> list[tuple[str, str, str]]:
    """Return (name, profile_href, image_url) for each player pod."""
    pods: list[tuple[str, str, str]] = []
    cdn_pat = CDN.replace("-", r"\-")
    blocks = re.findall(
        r"o-person-pod__inner[^>]*href=[\"']?(/players/[^\"'\s>]+)[^>]*>(.*?)o-person-pod__name[^>]*>([^<]+)<",
        html,
        re.DOTALL,
    )
    for href, block, name in blocks:
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
            pods.append((name.strip(), href, m.group(1) + "?width=560&height=668"))
    return pods


def is_wbbl_player(profile_href: str) -> bool:
    """True if player profile is primarily a WBBL / women's player."""
    url = "https://www.adelaidestrikers.com.au" + profile_href
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return False
        text = resp.text
        wbbl_count = len(re.findall(r"WBBL", text))
        bbl_count = len(re.findall(r"KFC BBL|BBL\|1", text))
        return wbbl_count > bbl_count or (wbbl_count >= 1 and bbl_count == 0)
    except Exception:
        return False


def download_image(url: str, save_path: Path) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200 and len(resp.content) > 500:
            save_path.write_bytes(resp.content)
            return True
        print(f"    FAIL HTTP {resp.status_code}")
        return False
    except Exception as exc:
        print(f"    FAIL Error: {exc}")
        return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("Adelaide Strikers BBL (Men's) Player Image Downloader")
    print("=" * 65)
    print(f"Fetching: {SOURCE_URL}\n")

    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    pods = fetch_player_pods(resp.text)
    print(f"Players found on page: {len(pods)}\n")

    ok = skip_wbbl = fail = 0
    skipped_names: list[str] = []

    for name, href, img_url in pods:
        print(f"  {name}")
        if is_wbbl_player(href):
            print(f"    SKIP WBBL player")
            skip_wbbl += 1
            skipped_names.append(name)
            time.sleep(0.2)
            continue

        save_path = OUTPUT_DIR / name_to_filename(name)
        print(f"    -> {save_path.name}")
        if download_image(img_url, save_path):
            print(f"    OK Official site ({save_path.stat().st_size:,} bytes)")
            ok += 1
        else:
            fail += 1
        time.sleep(0.3)

    print(f"\n{'=' * 65}")
    print(f"Done: {ok} downloaded, {skip_wbbl} WBBL skipped, {fail} failed")
    print(f"Saved to: {OUTPUT_DIR}")

    if skipped_names:
        print(f"\nWBBL players skipped ({len(skipped_names)}):")
        for p in skipped_names:
            print(f"  - {p}")


if __name__ == "__main__":
    main()
