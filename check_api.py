import urllib.request, json
url = 'http://127.0.0.1:8000/api/lessons/28/questions'
try:
    req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())
    for item in data:
        gt = item.get('group_title', '')
        if gt in ['Visual Matching', 'Fix the Mistake']:
            opts = item.get('options', {})
            if isinstance(opts, dict):
                print(f'--- {gt} ---')
                print(f'  question: {item.get("question", "")}')
                print(f'  instruction: {opts.get("instruction", "MISSING")}')
                print(f'  audio_text: {opts.get("audio_text", "MISSING")}')
except Exception as e:
    print(f'Error: {e}')
