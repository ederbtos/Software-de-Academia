import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from main import app

with TestClient(app) as client:
    # Login superadmin with follow_redirects
    print("=== SUPERADMIN LOGIN ===")
    r = client.post('/auth/login/form', data={'email': 'admin@sistema.com', 'password': 'Admin@123'}, follow_redirects=True)
    print(f'Login + follow: {r.status_code}')
    print(f'Final URL: {r.url}')
    if r.status_code >= 400:
        print(f'Error body: {r.text[:500]}')
    
    # Try directly with cookie
    print("\n=== DIRECT DASHBOARD WITH COOKIE ===")
    from app.core.security import create_access_token
    token = create_access_token({"sub": 1, "scope": "public", "role": "superadmin"})
    r2 = client.get('/dashboard', cookies={'access_token': token})
    print(f'GET /dashboard with public token: {r2.status_code}')
    if r2.status_code >= 400:
        print(f'Error: {r2.text[:300]}')
