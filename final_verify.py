import json, urllib.request

url = "http://127.0.0.1:8000/api/lessons/28/questions"
req = urllib.request.urlopen(url, timeout=10)
data = json.loads(req.read())

print("=== SERVER IS LIVE ===\n")

for a in data:
    gt = a.get('group_title', '?')
    at = a.get('activity_type')
    instr = a.get('options', {}).get('instruction', '(MISSING)')
    audio = a.get('options', {}).get('audio_text', '(none)')
    q = a.get('question', '')[:50]

    if gt in ['Match It!', 'Fix the Mistake', 'Comprehension Questions']:
        print(f"{gt} ({at})")
        print(f"  Instruction: {instr}")
        print(f"  Audio text: {audio}")
        print(f"  Question: {q}")
        print()
