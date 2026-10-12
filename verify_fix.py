import urllib.request, json
url = 'http://127.0.0.1:8000/api/lessons/28/questions'
req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())
# For each activity, show what instruction should be displayed and what Listen will read
for item in data:
    gt = item.get('group_title', '')
    at = item.get('activity_type', '')
    opts = item.get('options', {})
    if not isinstance(opts, dict):
        continue
    instruction = opts.get('instruction', '')
    question = item.get('question', '')
    audio_text = opts.get('audio_text', '')
    presentation = opts.get('presentation', '')
    # After fix, non-phonics Listen reads: instruction (since instructionText = instruction from renderActivity)
    if presentation == 'grade1_phonics':
        listen_reads = audio_text  # phonics reads word
    else:
        listen_reads = instruction  # after fix: only instruction
    on_screen = instruction
    match = listen_reads == on_screen if listen_reads and on_screen else True
    if not match:
        print(f'{gt} ({at}): MISMATCH')
        print(f'  On screen: {on_screen[:80]}')
        print(f'  Listen:    {listen_reads[:80]}')
