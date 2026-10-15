import json, urllib.request

url = "http://127.0.0.1:8000/api/lessons?grade=2"
req = urllib.request.urlopen(url, timeout=10)
lessons = json.loads(req.read())

WRONG = "Read or listen to the question, then choose the best answer."

for l in lessons:
    lid = l['id']
    url2 = f"http://127.0.0.1:8000/api/lessons/{lid}/questions"
    req2 = urllib.request.urlopen(url2, timeout=10)
    data = json.loads(req2.read())

    for a in data:
        gt = a.get('group_title', '?')
        instr = a.get('options', {}).get('instruction', '(MISSING)')
        if gt in ['Match It!', 'Visual Matching', 'Fix the Mistake']:
            is_wrong = instr == WRONG
            status = "WRONG!" if is_wrong else "OK"
            print(f"{l['title']:30s} | {gt:20s} | {status} | {instr[:80]}")
