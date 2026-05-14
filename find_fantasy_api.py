import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}

# Same Next.js app as ligue1.com - check the fantasy-specific chunk which likely has player data
r = requests.get('https://11type.lfp.fr/_next/static/chunks/pages/fantasy-204461b7a0c1781c.js', headers=headers, timeout=30)
text = r.text
print('Fantasy chunk size:', len(text))

# Write to file for inspection
with open('fantasy_chunk.js', 'w', encoding='utf-8') as f:
    f.write(text)
print('Saved to fantasy_chunk.js')

# Find all https URLs
https_matches = re.findall(r'https://[a-zA-Z0-9._/%-]{10,120}', text)
unique_domains = sorted(set([re.match(r'https://([a-zA-Z0-9._-]+)', u).group(1) for u in https_matches if u]))
print('Domains:', unique_domains)

# Find S3 and CDN patterns
for keyword in ['s3', 'player', 'image', 'photo', 'cdn', 'ligue1', 'portrait']:
    matches = [u for u in https_matches if keyword in u.lower()]
    if matches:
        print(f'\n{keyword} matches:')
        for m in list(set(matches))[:8]: print(' ', m)
