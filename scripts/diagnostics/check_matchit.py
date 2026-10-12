import json, urllib.request
lesson_id = 28  # A Dog's Life
url = f"http://127.0.0.1:8000/api/lessons/{lesson_id}/questions"
req = urllib.request.urlopen(url, timeout=10)
data = json.loads(req.read())
for a in data:
    if a.get('group_title') == 'Match It!':
        opts = a.get('options', {})
        instr = opts.get('instruction', '(MISSING)')
        at = a.get('activity_type')
        q = a.get('question')
        print(f"activity_type: {at}")
        print(f"question: {q}")
        print(f"instruction: {instr}")
        # Also check all keys in options
        print(f"options keys: {list(opts.keys())}")
        print()
