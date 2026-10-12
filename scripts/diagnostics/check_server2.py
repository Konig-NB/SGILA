import urllib.request, json

# Quick API check to verify server is running with current data
url = 'http://127.0.0.1:8000/api/lessons/28/questions'
req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())

# Check the response headers for caching
print("Response headers:")
for k, v in resp.headers.items():
    if 'cache' in k.lower() or 'pragma':
        print(f"  {k}: {v}")

# Find activity 3 (Visual Matching)
for item in data:
    gt = item.get('group_title', '')
    if gt in ['Visual Matching', 'Fix the Mistake', 'Match It!', 'Spelling']:
        opts = item.get('options', {})
        if isinstance(opts, dict):
            instr = opts.get('instruction', 'MISSING')[:80]
            print(f"{gt}: {instr}")
