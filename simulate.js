import json, urllib.request

lesson_id = 28
url = f"http://127.0.0.1:8000/api/lessons/{lesson_id}/questions"
req = urllib.request.urlopen(url, timeout=10)
data = json.loads(req.read())

print("=== What Listen reads vs what is displayed ===\n")

for a in data:
    gt = a.get('group_title', '?')
    if gt not in ['Match It!', 'Fix the Mistake', 'Comprehension Questions']:
        continue

    opts = a.get('options', {})
    instr = opts.get('instruction', '(MISSING)')
    question = a.get('question', '')
    audio_text = opts.get('audio_text', '(none)')
    atype = a.get('activity_type')

    print(f"--- {gt} (type: {atype}) ---")
    print(f"  On-screen instruction: {instr}")

    # Simulate renderActivityMedia for non-phonics
    if atype == 'multiple_choice' and audio_text:
        # Comprehension Questions path
        spoken = f"{instr}. {question}" if instr else question
        print(f"  Listen reads: {spoken}")
    elif atype == 'matching' and audio_text:
        # Match It! path (isReadingActivity = true, spokenText = instruction)
        spoken = instr if instr else question
        print(f"  Listen reads: {spoken}")
    elif atype == 'cloze' and audio_text:
        # Fix the Mistake path (isReadingActivity = true, spokenText = instruction)
        spoken = instr if instr else question
        print(f"  Listen reads: {spoken}")

    match = instr == spoken if instr != '(MISSING)' else False
    print(f"  MATCH: {match}")
    print()
