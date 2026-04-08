import urllib.request
import urllib.parse
import http.cookiejar

# Setup cookie jar
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

# POST login
data = urllib.parse.urlencode({'email': 'admin@sistema.com', 'password': 'Admin@123'}).encode()
req = urllib.request.Request('http://localhost:8000/auth/login/form', data=data, method='POST')

try:
    resp = opener.open(req)
    print(f'Login response: {resp.status}')
    print(f'URL: {resp.url}')
except urllib.error.HTTPError as e:
    print(f'Login error: {e.code}')
    body = e.fp.read().decode()
    print(f'Body: {body[:300]}')

print(f'\nCookies: {list(cookie_jar)}')

# Now try superadmin page
try:
    resp2 = opener.open('http://localhost:8000/superadmin')
    print(f'Superadmin: {resp2.status}')
    body = resp2.read().decode()
    print(f'Body (first 200): {body[:200]}')
except urllib.error.HTTPError as e:
    print(f'Superadmin error: {e.code}')
    body = e.fp.read().decode()
    if e.code == 500:
        print(f'Error: {body[:500]}')
    else:
        print(f'Error body: {body[:200]}')
