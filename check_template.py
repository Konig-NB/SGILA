import urllib.request
url = "http://127.0.0.1:8000/lessons/28/questions"
req = urllib.request.urlopen(url, timeout=10)
html = req.read().decode('utf-8')
print(f"Length: {len(html)}")
print(f"First 500 chars: {html[:500]}")
# Check if it's a redirect
print(f"Status: {req.status}")
print(f"URL: {req.url}")
# Check for key strings
for s in ["questions.html", "activity-instruction", "renderActivity", "questions"]:
    print(f"'{s}' found: {s in html}")
