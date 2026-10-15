import json, urllib.request

url = "http://127.0.0.1:8000/api/lessons/28/questions"
req = urllib.request.urlopen(url, timeout=10)
data = json.loads(req.read())

for a in data:
    gt = a.get('group_title', '?')
    if gt in ['Match It!', 'Visual Matching', 'Fix the Mistake', 'Comprehension Questions']:
        instr = a.get('options', {}).get('instruction', '(MISSING)')
        q = a.get('question', '')[:40]
        at = a.get('activity_type')
        print(f"{gt:25s} | {at:15s} | Q: {q}")
        print(f"  instr: {instr}")
        print()
