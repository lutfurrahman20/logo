import requests, re, json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36', 'Accept': 'application/json'}

# Fetch the bundle
r = requests.get('https://profile.ligue1.fr/static/js/main.41078e8d.js', headers=headers, timeout=15)
text = r.text
print('Bundle size:', len(text))

# Find the api-dsp.myligue.fr usage context - get surrounding code
positions = [m.start() for m in re.finditer('api-dsp', text)]
print(f'Found {len(positions)} occurrences of api-dsp')
for pos in positions[:5]:
    snippet = text[max(0,pos-100):pos+200]
    print('---')
    print(snippet)

# Also search for image URL patterns in the bundle
print('\n=== IMAGE PATTERNS ===')
img_patterns = re.findall(r'["\']([^"\']*(?:photo|portrait|body|kit|jersey|maillot|player-img|joueur)[^"\']{0,100})["\']', text, re.IGNORECASE)
for p in img_patterns[:20]:
    print(' ', p)

# Search for S3 ligue1
print('\n=== S3 ligue1 ===')
s3_l1 = re.findall(r'["\']([^"\']*ligue1[^"\']{0,100})["\']', text)
for p in s3_l1[:20]:
    print(' ', p)
