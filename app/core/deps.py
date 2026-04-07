"""
Dependências de autenticação e extração do tenant (schema) a partir do host.
"""
from typing import Optional
from fastapi import Request, Depends, HTTPException, status, Cookie
from sqlalchemy.orm import Session
from app.db.database import get_db, get_tenant_db
from app.core.security import decode_token
from app.models.public import UsuarioPublic, Academia


def get_current_token(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip() or None
    return token


def get_current_user_public(
    request: Request,
    db: Session = Depends(get_db),
) -> UsuarioPublic:
    token = get_current_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    payload = decode_token(token)
    if not payload or payload.get("scope") != "public":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = db.query(UsuarioPublic).filter(UsuarioPublic.id == payload["sub"]).first()
    if not user or not user.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo")
    return user


def require_superadmin(user: UsuarioPublic = Depends(get_current_user_public)) -> UsuarioPublic:
    if user.role.value != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return user


def get_schema_from_request(request: Request, db: Session = Depends(get_db)) -> str:
    """Extrai o slug do subdomínio e devolve o schema_name da academia."""
    host = request.headers.get("host", "")
    slug = host.split(".")[0]
    academia = db.query(Academia).filter(Academia.slug == slug).first()
    if not academia or academia.status.value != "ativa":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academia não encontrada")
    return academia.schema_name


def get_tenant_session(
    schema: str = Depends(get_schema_from_request),
):
    """Gera sessão DB com search_path configurado para o tenant."""
    yield from get_tenant_db(schema)


def get_current_funcionario(
    request: Request,
    db: Session = Depends(get_tenant_session),
):
    from app.models.tenant import Funcionario
    token = get_current_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    payload = decode_token(token)
    if not payload or payload.get("scope") != "tenant":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    func = db.query(Funcionario).filter(Funcionario.id == payload["sub"]).first()
    if not func or not func.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Funcionário inativo")
    return func


def require_professor_or_admin(func=Depends(get_current_funcionario)):
    if func.role.value not in ("admin", "professor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return func


def require_admin(func=Depends(get_current_funcionario)):
    if func.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return func
