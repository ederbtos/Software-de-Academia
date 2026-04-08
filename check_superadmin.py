import sys
sys.path.insert(0, '.')
from app.db.database import get_db
from app.models.public import UsuarioPublic

db = next(get_db())
try:
    user = db.query(UsuarioPublic).filter(UsuarioPublic.email == 'admin@sistema.com').first()
    if user:
        print(f'Superadmin encontrado: {user.nome} ({user.email})')
        print(f'ID: {user.id}')
        print(f'Role: {user.role}')
        print(f'Ativo: {user.ativo}')
    else:
        print('Superadmin NAO encontrado!')
finally:
    db.close()
