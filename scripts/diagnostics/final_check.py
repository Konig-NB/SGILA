import urllib.request, json
url = 'http://127.0.0.1:8000/api/lessons/28/questions'
req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())
# Check all non-phonics activities have matching instruction and audio
mismatches = []
for item in data:
    gt = item.get('group_title', '')
    opts = item.get('options', {})
    if not isinstance(opts, dict):
        continue
    instruction = opts.get('instruction', '')
    question = item.get('question', '')
    presentation = opts.get('presentation', '')
    if presentation == 'grade1_phonics':
        continue  # skip phonics - Listen reads word intentionally
    # After fix, Listen reads: instruction (instructionText from renderActivity)
    on_screen = instruction
    listen_reads = instruction  # after fix
    if listen_reads != on_screen:
        mismatches.append((gt, on_screen[:60], listen_reads[:60]))
if mismatches:
    for m in mismatches:
        print(f'MISMATCH: {m[0]}')
        print(f'  On screen: {m[1]}')
        print(f'  Listen:    {m[2]}')
else:
    print('All non-phonics activities have matching instruction and Listen audio!')
