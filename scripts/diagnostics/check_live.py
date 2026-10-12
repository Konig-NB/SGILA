import urllib.request
url = 'http://127.0.0.1:8000/lessons/28/questions'
req = urllib.request.Request(url)
resp = urllib.request.urlopen(req, timeout=10)
content = resp.read().decode()
print(f'Status: {resp.status}')
print(f'Content length: {len(content)}')
print(f'Has renderActivity: {"function renderActivity" in content}')
print(f'Has activity-instruction: {"activity-instruction" in content}')
print(f'Has Look at the picture: {"Look at the picture" in content}')
print(f'Has One word: {"One word in this sentence" in content}')
print(f'First 500 chars after <body>:')
body_idx = content.find('<body')
if body_idx >= 0:
    print(content[body_idx:body_idx+500])
