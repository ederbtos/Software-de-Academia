from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.public import Academia, UsuarioPublic, UsuarioPublicRole
from app.models.tenant import Funcionario
from app.schemas.public import LoginRequest, TokenOut
from app.schemas.tenant import FuncionarioLoginRequest
from app.core.security import verify_password, create_access_token


def login_public(data: LoginRequest, db: Session) -> TokenOut:
    user = db.query(UsuarioPublic).filter(UsuarioPublic.email == data.email).first()
    if not user or not verify_password(data.password, user.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo")

    slug = None
    if user.academia_id:
        academia = db.query(Academia).filter(Academia.id == user.academia_id).first()
        slug = academia.slug if academia else None

    token = create_access_token({"sub": user.id, "scope": "public", "role": user.role.value})
    return TokenOut(access_token=token, role=user.role.value, academia_slug=slug)


def login_tenant(data: FuncionarioLoginRequest, db: Session) -> TokenOut:
    func = db.query(Funcionario).filter(Funcionario.email == data.email).first()
    if not func or not verify_password(data.password, func.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if not func.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Funcionário inativo")

    token = create_access_token({"sub": func.id, "scope": "tenant", "role": func.role.value})
    return TokenOut(access_token=token, role=func.role.value)
