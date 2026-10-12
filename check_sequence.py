import urllib.request, json
url = 'http://127.0.0.1:8000/api/lessons/28/questions'
req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())
for i, item in enumerate(data):
    gt = item.get('group_title', '')
    at = item.get('activity_type', '')
    q = item.get('question', '')[:60]
    inst = ''
    opts = item.get('options', {})
    if isinstance(opts, dict):
        inst = opts.get('instruction', '')[:80]
    print(f'[{i}] group={item.get("group_number")}, title="{gt}", type={at}')
    print(f'     Q: {q}...')
    print(f'     I: {inst}...')
