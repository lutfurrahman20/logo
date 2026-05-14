import requests, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}

# Fetch MPG JS bundle to find API routes
r = requests.get('https://mpg.football/build/manifest-E78FED4D.js', headers=headers, timeout=15)
text = r.text
print('Manifest size:', len(text))

# Find all URLs in the manifest
urls = re.findall(r'https://[^\s"\'<>]{10,100}', text)
print('URLs:', list(set(urls))[:20])

# Get the entry.client bundle
r2 = requests.get('https://mpg.football/build/entry.client-ELBAFXSQ.js', headers=headers, timeout=15)
text2 = r2.text
print('\nEntry bundle size:', len(text2))
api_routes = re.findall(r'["\'](/api/[^"\']{3,60})["\']', text2)
print('API routes:', list(set(api_routes))[:20])

# Also find player image CDN patterns
img_patterns = re.findall(r'https://[^\s"\']{20,100}(?:player|portrait|photo|kit)[^\s"\']{0,50}', text2, re.I)
print('Player img patterns:', img_patterns[:10])

# S3 patterns
s3 = re.findall(r'https://[^\s"\']{5,100}s3[^\s"\']{5,80}', text2)
print('S3 patterns:', list(set(s3))[:10])
