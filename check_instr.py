import json, urllib.request
lesson_id = 28  # A Dog's Life
url = f"http://127.0.0.1:8000/api/lessons/{lesson_id}/questions"
try:
    req = urllib.request.urlopen(url, timeout=10)
    data = json.loads(req.read())
    for a in data:
        gt = a.get('group_title', '?')
        at = a.get('activity_type', '?')
        instr = a.get('options', {}).get('instruction', '(none)')
        if gt in ['Match It!', 'Fix the Mistake', 'Comprehension Questions']:
            q = a.get('question', '')[:70]
            print(f"--- {gt} ({at}) ---")
            print(f"  Question: {q}")
            print(f"  Instruction: {instr}")
            print()
except Exception as e:
    print(f"Error: {e}")
