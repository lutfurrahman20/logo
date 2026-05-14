import requests
import re
from bs4 import BeautifulSoup

# Test a few different ESPN CDN patterns
player_id = "84774"  # Manuel Neuer

cdn_patterns = [
    f"https://a.espncdn.com/i/headshots/soccer/players/full/{player_id}.png",
    f"https://a.espncdn.com/combiner/i?img=/i/headshots/soccer/players/full/{player_id}.png",
    f"https://a.espncdn.com/combiner/i?img=/i/headshots/soccer/players/full/{player_id}.jpg",
    f"https://a.espncdn.com/i/headshots/soccer/players/full/{player_id}.jpg",
    f"https://a.espncdn.com/photo/2023/0101/r{player_id}_600x600_1-1.jpg",
    f"https://secure.espncdn.com/combiner/i?img=/i/headshots/soccer/players/full/{player_id}.png",
]

print("Testing different CDN patterns:")
for pattern in cdn_patterns:
    try:
        r = requests.head(pattern, timeout=5, allow_redirects=True)
        print(f"  {r.status_code} - {pattern}")
    except Exception as e:
        print(f"  Error - {pattern}")

# Try scraping from player page
print("\nScraping from player page:")
player_url = f"https://www.espn.com/soccer/player/_/id/{player_id}/manuel-neuer"
try:
    response = requests.get(player_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for player image
    imgs = soup.find_all('img')
    player_imgs = []
    for img in imgs:
        src = img.get('src') or img.get('data-src') or ''
        if any(x in src for x in ['player', 'headshot', 'athlete']):
            player_imgs.append(src)
    
    print(f"Found {len(player_imgs)} potential player images:")
    for img_url in player_imgs[:5]:
        print(f"  {img_url}")
    
    # Also look for og:image meta tag
    og_image = soup.find('meta', property='og:image')
    if og_image:
        print(f"\nOG Image: {og_image.get('content')}")
        
except Exception as e:
    print(f"Error scraping player page: {e}")
