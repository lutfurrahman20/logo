import requests, re, unicodedata
h = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9', 'Referer': 'https://www.transfermarkt.com/'}

# Check extended kader (full squad incl. reserves) for 2025/26
r_ext = requests.get('https://www.transfermarkt.com/afc-bournemouth/kader/verein/989/plus/1', headers=h, timeout=20)
imgs_ext = re.findall(r'data-src="([^"]*transfermarkt[^"]*portrait/medium/[^"]+)"\s[^>]*?alt="([^"]+)"', r_ext.text)
print(f'Extended kader (+reserves): {len(imgs_ext)} players')
for url, name in imgs_ext:
    if any(p.lower() in name.lower() for p in ['bevan', 'dacosta', 'rees', 'stevens']):
        print(f'  FOUND: {name} -> {url}')
print('All names:', [n for _, n in imgs_ext])
print('---')


r = requests.get('https://www.transfermarkt.com/afc-bournemouth/kader/verein/989', headers=h, timeout=20)

player_imgs = re.findall(r'data-src=["\']([^\'"]*transfermarkt[^\'"]*portrait/medium/[^"\']+)["\'][^>]*?alt=["\']([^"\']+)["\']', r.text)
print(f'pairs found: {len(player_imgs)}')

# Build lookup
tm_lookup = {}
for url, alt in player_imgs:
    name = alt.strip()
    tm_lookup[name] = url
    print(f'  {name:35} {url}')

# Check ESPN squad coverage
espn_squad = ['Fraser Forster', 'Christos Mandas', 'Djordje Petrovic', 'Adam Smith',
    'Marcos Senesi', 'James Hill', 'Bafode Diakite', 'Adrien Truffert', 'Matai Akinmboni',
    'Julio Soler', 'Owen Bevan', 'Alex Jimenez', 'Veljko Milosavljevic', 'David Brooks',
    'Ryan Christie', 'Tyler Adams', 'Lewis Cook', 'Marcus Tavernier', 'Alex Scott',
    'Alex Toth', 'Malcom Dacosta', 'Charlie Stevens', 'Evanilson', 'Enes Unal',
    'Justin Kluivert', 'Amine Adli', 'Ben Gannon Doak', 'Rayan', 'Junior Kroupi', 'Remy Rees-Dottin']

def norm(s):
    return unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()

print('\nMatching check:')
for p in espn_squad:
    matched = [(k, v) for k, v in tm_lookup.items() if norm(p) in norm(k) or norm(k) in norm(p)]
    if matched:
        print(f'  OK {p} -> {matched[0][0]}')
    else:
        print(f'  MISS {p}')
