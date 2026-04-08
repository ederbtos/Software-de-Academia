import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from main import app

with TestClient(app) as client:
    # Test superadmin login
    r = client.post('/auth/login/form', data={'email': 'admin@sistema.com', 'password': 'Admin@123'})
    print(f'Login POST: {r.status_code}')
    
    # Test root
    r2 = client.get('/')
    print(f'GET /: {r2.status_code}')
    print(f'URL: {r2.url}')
    
    # Test dashboard without auth
    r3 = client.get('/dashboard')
    print(f'GET /dashboard no auth: {r3.status_code}')
    if r3.status_code >= 400:
        print(f'Error: {r3.text[:500]}')
