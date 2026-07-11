"""
Fallback logo sources for cricket team logo scrapers.
Used when ESPN CDN does not have a team logo.
"""

from __future__ import annotations

import io
import re
import time
from pathlib import Path

import requests
from PIL import Image

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
WIKI_HEADERS = {"User-Agent": "LogoScraper/1.0 (contact: local)"}
TSDB_API = "https://www.thesportsdb.com/api/v1/json/3"


def wiki_title_aliases(team_name: str) -> list[str]:
    """Build likely Wikipedia page titles for a team."""
    titles = [team_name]
    if team_name == "West Indies":
        titles.append("West Indies cricket team")
    elif "national cricket team" not in team_name.lower():
        titles.append(f"{team_name} national cricket team")
    return titles


def fetch_from_thesportsdb(
    team_name: str,
    league: str | None = None,
    aliases: list[str] | None = None,
) -> str | None:
    """Return a logo URL from TheSportsDB, or None."""
    search_names = [team_name] + (aliases or [])
    league_lower = (league or "").lower()

    for query in search_names:
        try:
            resp = requests.get(
                f"{TSDB_API}/searchteams.php",
                params={"t": query},
                headers=HEADERS,
                timeout=15,
            )
            for team in resp.json().get("teams") or []:
                badge = team.get("strTeamBadge") or team.get("strBadge")
                if not badge:
                    continue
                team_league = (team.get("strLeague") or "").lower()
                team_label = (team.get("strTeam") or "").lower()
                if league_lower and league_lower not in team_league:
                    if query.lower() not in team_label and team_name.lower() not in team_label:
                        continue
                return badge
        except Exception:
            pass
        time.sleep(0.2)

    if league:
        try:
            resp = requests.get(
                f"{TSDB_API}/search_all_teams.php",
                params={"l": league},
                headers=HEADERS,
                timeout=15,
            )
            for team in resp.json().get("teams") or []:
                label = team.get("strTeam") or ""
                if team_name.lower() not in label.lower() and label.lower() not in team_name.lower():
                    continue
                badge = team.get("strTeamBadge") or team.get("strBadge")
                if badge:
                    return badge
        except Exception:
            pass

    return None


def fetch_from_wikipedia(
    team_name: str,
    title_aliases: list[str] | None = None,
) -> str | None:
    """Return an infobox logo URL from Wikipedia, or None."""
    titles = title_aliases or wiki_title_aliases(team_name)

    for title in titles:
        try:
            time.sleep(0.8)
            resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "parse", "page": title, "prop": "text", "format": "json"},
                headers=WIKI_HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            html = resp.json().get("parse", {}).get("text", {}).get("*", "")
            if not html:
                continue

            for pat in (
                r'class="infobox-image"[^>]*>.*?src="(//upload\.wikimedia\.org[^"]+)"',
                r'class="infobox-image"[^>]*>.*?src="(https://upload\.wikimedia\.org[^"]+)"',
            ):
                match = re.search(pat, html, re.S | re.I)
                if not match:
                    continue
                url = match.group(1)
                if url.startswith("//"):
                    url = "https:" + url
                return url
        except Exception:
            pass

    return None


def save_logo_bytes(content: bytes, save_path: Path) -> bool:
    """Save image bytes as PNG."""
    if len(content) < 500:
        return False
    try:
        if save_path.suffix.lower() == ".png" and content[:8] == b"\x89PNG\r\n\x1a\n":
            save_path.write_bytes(content)
            return True
        img = Image.open(io.BytesIO(content))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        elif img.mode == "RGB":
            img = img.convert("RGBA")
        img.save(save_path, "PNG")
        return True
    except Exception:
        return False


def download_logo(url: str, save_path: Path, headers: dict | None = None) -> bool:
    """Download a logo URL and save as PNG."""
    try:
        resp = requests.get(url, headers=headers or HEADERS, timeout=20)
        if resp.status_code != 200:
            return False
        return save_logo_bytes(resp.content, save_path)
    except Exception:
        return False


def download_with_fallbacks(
    team_name: str,
    primary_url: str,
    save_path: Path,
    *,
    league: str | None = None,
    tsdb_aliases: list[str] | None = None,
    wiki_titles: list[str] | None = None,
    headers: dict | None = None,
) -> tuple[bool, str]:
    """
    Try ESPN URL first, then TheSportsDB, then Wikipedia.
    Returns (success, source_name).
    """
    h = headers or HEADERS

    if download_logo(primary_url, save_path, headers=h):
        return True, "ESPN"

    print("    ESPN failed - trying TheSportsDB...")
    tsdb_url = fetch_from_thesportsdb(team_name, league=league, aliases=tsdb_aliases)
    if tsdb_url and download_logo(tsdb_url, save_path, headers=h):
        return True, "TheSportsDB"

    print("    TheSportsDB failed - trying Wikipedia...")
    wiki_url = fetch_from_wikipedia(team_name, title_aliases=wiki_titles)
    if wiki_url and download_logo(wiki_url, save_path, headers=WIKI_HEADERS):
        return True, "Wikipedia"

    return False, ""
