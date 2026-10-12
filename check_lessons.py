import json, urllib.request
url = "http://127.0.0.1:8000/api/lessons?grade=2"
try:
    req = urllib.request.urlopen(url, timeout=10)
    data = json.loads(req.read())
    print(f"Found {len(data)} grade 2 lessons:")
    for l in data:
        print(f"  id={l.get('id')}: {l.get('title')}")
except Exception as e:
    print(f"Error: {e}")
