import urllib.request

# Check what the server returns for the login page vs questions page
url = 'http://127.0.0.1:8000/lessons/28/questions'
req = urllib.request.Request(url)
resp = urllib.request.urlopen(req, timeout=10)
content = resp.read().decode()

# Check headers
print("Status:", resp.status)
print("Headers:", dict(resp.headers))
print(f"\nContent length: {len(content)}")
print(f"Content type: {resp.headers.get('Content-Type', 'unknown')}")

# Check if it's a redirect
if resp.status in [301, 302, 303, 307, 308]:
    print(f"Redirect to: {resp.headers.get('Location', 'unknown')}")
elif len(content) < 5000:
    print(f"\nContent preview (first 500 chars):")
    print(content[:500])
