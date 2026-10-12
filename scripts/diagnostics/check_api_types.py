import urllib.request, json
url = 'http://127.0.0.1:8000/api/lessons/28/questions'
req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())
# Find Visual Matching and Fix the Mistake
for item in data:
    gt = item.get('group_title', '')
    if gt in ['Visual Matching', 'Fix the Mistake']:
        print(f'--- {gt} (index {data.index(item)}) ---')
        print(f'  group_title type: {type(item.get("group_title"))}')
        print(f'  group_title value: "{item.get("group_title")}"')
        opts = item.get('options', {})
        print(f'  options type: {type(opts)}')
        if isinstance(opts, dict):
            instr = opts.get('instruction')
            print(f'  instruction type: {type(instr)}')
            print(f'  instruction value: "{instr}"')
            at = opts.get('audio_text')
            print(f'  audio_text value: "{at}"')
        print()
