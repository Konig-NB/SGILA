import urllib.request, json
url = 'http://127.0.0.1:8000/api/lessons/28/questions'
req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())
for item in data:
    gt = item.get('group_title', '')
    if gt in ['Visual Matching', 'Fix the Mistake']:
        opts = item.get('options', {})
        if isinstance(opts, dict):
            print(f'{gt}: {opts.get("instruction")[:100]}')
