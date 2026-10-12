import urllib.request, json
url = 'http://127.0.0.1:8000/api/lessons/28/questions'
req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())
# Verify that for each activity, the instruction and question are handled correctly
for item in data:
    gt = item.get('group_title', '')
    opts = item.get('options', {})
    if not isinstance(opts, dict):
        continue
    instruction = opts.get('instruction', '')
    question = item.get('question', '')
    if not instruction and not question:
        continue
    # Simulate the hasOverlap logic
    has_overlap = instruction and question and question in instruction
    if has_overlap:
        print(f'{gt}: instruction includes question (highlight instruction only, read instruction)')
    else:
        print(f'{gt}: instruction differs from question (highlight BOTH, read instruction + question)')
