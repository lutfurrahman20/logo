"""
New England Patriots - Player Headshot Scraper
Scrapes player photos from https://www.patriots.com/team/players-roster/
Uses Selenium (headless Chrome) to handle JavaScript-rendered pages.
"""

import os
import re
import time
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ─────────────────────────────────────────────────────────────────────
ROSTER_URL   = "https://www.patriots.com/team/players-roster/"
OUTPUT_DIR   = Path("f:/logo/patriots_player_logos")
DELAY        = 1.5          # seconds to wait between page loads (be polite)
HEADLESS     = True         # set False to watch the browser

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
# ───────────────────────────────────────────────────────────────────────────────


def make_driver() -> webdriver.Chrome:
    """Create a headless Chrome WebDriver."""
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


def safe_filename(name: str) -> str:
    """Convert a player name to a safe filename."""
    name = name.strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower()


def get_player_links(driver: webdriver.Chrome) -> list[dict]:
    """
    Load the roster page and collect all player profile URLs + names.
    Returns a list of {'name': str, 'url': str} dicts.
    """
    print(f"\n📋 Loading roster page: {ROSTER_URL}")
    driver.get(ROSTER_URL)

    # Wait until player links appear (they live inside <a> tags with href matching /players-roster/<slug>/)
    wait = WebDriverWait(driver, 20)
    try:
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[href*='/team/players-roster/']")
            )
        )
    except Exception:
        print("  ⚠️  Timed out waiting for player links – trying anyway …")

    time.sleep(2)  # let lazy-loaded content settle

    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/team/players-roster/']")

    players = []
    seen_urls = set()

    for a in anchors:
        href = a.get_attribute("href") or ""
        # Filter: must end with a slug (not just the root roster page)
        if not re.search(r"/team/players-roster/[a-z0-9\-]+/?$", href):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)

        # Try to get the name from the link text; fall back to slug
        text = a.text.strip()
        if not text:
            slug = href.rstrip("/").split("/")[-1]
            text = slug.replace("-", " ").title()

        players.append({"name": text, "url": href})

    print(f"  ✅ Found {len(players)} unique player profiles")
    return players


def get_headshot_url(driver: webdriver.Chrome, player_url: str) -> str | None:
    """
    Visit a player profile page and locate the headshot <img>.
    NFL headshots live at static.clubs.nfl.com with alt text containing 'headshot'.
    """
    driver.get(player_url)
    time.sleep(DELAY)

    # Strategy 1: look for img whose alt contains 'headshot'
    imgs = driver.find_elements(By.CSS_SELECTOR, "img[alt*='headshot'], img[alt*='Headshot']")
    for img in imgs:
        src = img.get_attribute("src") or ""
        if "static.clubs.nfl.com" in src or "static.nfl.com" in src or "nfl.com" in src:
            return src

    # Strategy 2: any img from the known CDN domain
    imgs = driver.find_elements(By.CSS_SELECTOR, "img[src*='static.clubs.nfl.com']")
    for img in imgs:
        src = img.get_attribute("src") or ""
        if src:
            return src

    # Strategy 3: any img from nfl CDN
    imgs = driver.find_elements(By.CSS_SELECTOR, "img[src*='nfl.com/image']")
    for img in imgs:
        src = img.get_attribute("src") or ""
        if src:
            return src

    return None


def upgrade_image_url(url: str) -> str:
    """
    Strip ALL Cloudinary transforms so we download the raw uploaded headshot
    with no landscape/cover crop applied.
    e.g. /image/upload/t_landscape_tablet/f_png/...  →  /image/upload/f_png/...
    """
    # Remove every t_<transform>/ segment
    url = re.sub(r"t_[^/]+/", "", url)
    # Ensure PNG output
    if "f_png" not in url:
        url = url.replace("/image/upload/", "/image/upload/f_png/")
    # Clean up any double-slashes left over
    url = re.sub(r"(?<!:)//+", "/", url)
    return url


def download_image(url: str, filepath: Path) -> bool:
    """Download an image from url and save to filepath."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 1000:
            filepath.write_bytes(r.content)
            return True
        print(f"    ⚠️  HTTP {r.status_code} or tiny file — skipped")
    except Exception as e:
        print(f"    ❌ Download error: {e}")
    return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  NEW ENGLAND PATRIOTS — Player Headshot Scraper")
    print("=" * 60)
    print(f"  Output folder : {OUTPUT_DIR}")

    driver = make_driver()
    results = {"downloaded": 0, "skipped": 0, "no_image": 0}

    try:
        players = get_player_links(driver)

        if not players:
            print("\n❌ No players found. The page structure may have changed.")
            return

        print(f"\n🚀 Downloading headshots for {len(players)} players …\n")

        for i, player in enumerate(players, 1):
            name = player["name"]
            url  = player["url"]
            safe = safe_filename(name)
            out_path = OUTPUT_DIR / f"{safe}.png"

            print(f"[{i:>3}/{len(players)}] {name}")

            if out_path.exists() and out_path.stat().st_size > 1000:
                print(f"         ↳ Already exists – skipping")
                results["skipped"] += 1
                continue

            img_url = get_headshot_url(driver, url)
            if not img_url:
                print(f"         ↳ ⚠️  No headshot found")
                results["no_image"] += 1
                continue

            # Upgrade to full-res
            img_url_hd = upgrade_image_url(img_url)
            print(f"         ↳ {img_url_hd}")

            success = download_image(img_url_hd, out_path)
            if not success:
                # Fall back to original URL
                success = download_image(img_url, out_path)

            if success:
                size_kb = out_path.stat().st_size / 1024
                print(f"         ↳ ✅ Saved ({size_kb:.1f} KB)")
                results["downloaded"] += 1
            else:
                results["no_image"] += 1

            time.sleep(DELAY)

    finally:
        driver.quit()

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  ✅ Downloaded : {results['downloaded']}")
    print(f"  ⏭️  Skipped   : {results['skipped']}")
    print(f"  ⚠️  No image  : {results['no_image']}")
    print(f"  📁 Saved to  : {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
