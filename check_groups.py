import json, urllib.request

url = "http://127.0.0.1:8000/api/lessons/28/questions"
req = urllib.request.urlopen(url, timeout=10)
data = json.loads(req.read())

for a in data:
    gt = a.get('group_title', '')
    gt_repr = repr(gt)
    at = a.get('activity_type', '')
    instr = a.get('options', {}).get('instruction', '(MISSING)')
    if gt in ['Match It!', 'Visual Matching', 'Fix the Mistake', 'Comprehension Questions']:
        print(f"{gt_repr:30s} | {at:15s} | instr_starts: {instr[:50]!r}")
