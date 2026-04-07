from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.public import LoginRequest, TokenOut, AcademiaCreate, AcademiaOut, UsuarioPublicCreate, UsuarioPublicOut
from app.schemas.tenant import FuncionarioLoginRequest
from app.services.auth import login_public, login_tenant
from app.services.academia import listar_academias, criar_academia, atualizar_academia, criar_usuario_publico
from app.core.deps import require_superadmin, get_tenant_session
from app.schemas.public import AcademiaUpdate

router = APIRouter()


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    token_out = login_public(data, db)
    response.set_cookie("access_token", token_out.access_token, httponly=True, samesite="lax")
    return token_out


@router.post("/auth/login/academia", response_model=TokenOut)
def login_academia(data: FuncionarioLoginRequest, response: Response, db: Session = Depends(get_tenant_session)):
    token_out = login_tenant(data, db)
    response.set_cookie("access_token", token_out.access_token, httponly=True, samesite="lax")
    return token_out


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"detail": "Logout realizado"}


# ---------------------------------------------------------------------------
# Academias (superadmin)
# ---------------------------------------------------------------------------

@router.get("/superadmin/academias", response_model=list[AcademiaOut])
def get_academias(db: Session = Depends(get_db), _=Depends(require_superadmin)):
    return listar_academias(db)


@router.post("/superadmin/academias", response_model=AcademiaOut, status_code=201)
def post_academia(data: AcademiaCreate, db: Session = Depends(get_db), _=Depends(require_superadmin)):
    return criar_academia(data, db)


@router.patch("/superadmin/academias/{academia_id}", response_model=AcademiaOut)
def patch_academia(academia_id: int, data: AcademiaUpdate, db: Session = Depends(get_db), _=Depends(require_superadmin)):
    return atualizar_academia(academia_id, data, db)


@router.post("/superadmin/usuarios", response_model=UsuarioPublicOut, status_code=201)
def post_usuario_publico(data: UsuarioPublicCreate, db: Session = Depends(get_db), _=Depends(require_superadmin)):
    return criar_usuario_publico(data, db)
