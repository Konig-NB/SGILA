import json, urllib.request
# Check ALL lessons for any Match It! with wrong instruction
url = "http://127.0.0.1:8000/api/lessons?grade=2"
req = urllib.request.urlopen(url, timeout=10)
lessons = json.loads(req.read())

wrong = []
for l in lessons:
    lid = l['id']
    url2 = f"http://127.0.0.1:8000/api/lessons/{lid}/questions"
    req2 = urllib.request.urlopen(url2, timeout=10)
    data = json.loads(req2.read())
    for a in data:
        if a.get('group_title') == 'Match It!':
            instr = a.get('options', {}).get('instruction', '(MISSING)')
            if 'Read or listen' in instr or 'choose the best answer' in instr:
                wrong.append((l['title'], instr))
            else:
                print(f"{l['title']}: OK - {instr[:80]}...")

if wrong:
    print("\nWRONG INSTRUCTIONS FOUND:")
    for title, instr in wrong:
        print(f"  {title}: {instr}")
else:
    print("\nNo wrong instructions found for Match It!")
