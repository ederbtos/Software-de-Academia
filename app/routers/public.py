from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.public import (
    LoginRequest,
    TokenOut,
    AcademiaCreate,
    AcademiaOut,
    UsuarioPublicCreate,
    UsuarioPublicOut,
    AuditLogOut,
    AuditMetricasOut,
)
from app.schemas.tenant import FuncionarioLoginRequest
from app.services.auth import login_public, login_tenant
from app.services.academia import listar_academias, criar_academia, atualizar_academia, criar_usuario_publico
from app.core.deps import require_superadmin, get_tenant_session
from app.schemas.public import AcademiaUpdate
from app.core.config import get_settings
from app.models.public import AuditLog

router = APIRouter()
settings = get_settings()


def _is_secure_cookie() -> bool:
    return settings.app_env.lower() in ("prod", "production")


@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    token_out = login_public(data, db)
    response.set_cookie(
        "access_token",
        token_out.access_token,
        httponly=True,
        samesite="lax",
        secure=_is_secure_cookie(),
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return token_out


@router.post("/auth/login/academia", response_model=TokenOut)
def login_academia(data: FuncionarioLoginRequest, response: Response, db: Session = Depends(get_tenant_session)):
    token_out = login_tenant(data, db)
    response.set_cookie(
        "access_token",
        token_out.access_token,
        httponly=True,
        samesite="lax",
        secure=_is_secure_cookie(),
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return token_out


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
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


@router.get("/superadmin/auditoria", response_model=list[AuditLogOut])
def get_auditoria(
    acao: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    data_inicio: str | None = Query(default=None, description="YYYY-MM-DD"),
    data_fim: str | None = Query(default=None, description="YYYY-MM-DD"),
    ordem: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=100, ge=10, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    q = db.query(AuditLog)
    if acao:
        q = q.filter(AuditLog.action.ilike(f"%{acao}%"))
    if actor_id:
        q = q.filter(AuditLog.actor_id == actor_id)
    if data_inicio:
        dt_ini = datetime.fromisoformat(data_inicio)
        q = q.filter(AuditLog.criado_em >= dt_ini)
    if data_fim:
        dt_fim = datetime.fromisoformat(data_fim) + timedelta(days=1)
        q = q.filter(AuditLog.criado_em < dt_fim)
    order_col = AuditLog.criado_em.asc() if ordem == "asc" else AuditLog.criado_em.desc()
    return q.order_by(order_col).offset(offset).limit(limit).all()


@router.get("/superadmin/auditoria/metricas", response_model=AuditMetricasOut)
def get_auditoria_metricas(
    acao: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    data_inicio: str | None = Query(default=None, description="YYYY-MM-DD"),
    data_fim: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    from sqlalchemy import func

    q = db.query(AuditLog)
    if acao:
        q = q.filter(AuditLog.action.ilike(f"%{acao}%"))
    if actor_id:
        q = q.filter(AuditLog.actor_id == actor_id)
    if data_inicio:
        dt_ini = datetime.fromisoformat(data_inicio)
        q = q.filter(AuditLog.criado_em >= dt_ini)
    if data_fim:
        dt_fim = datetime.fromisoformat(data_fim) + timedelta(days=1)
        q = q.filter(AuditLog.criado_em < dt_fim)

    total_eventos = q.count()

    top_acoes_raw = (
        q.with_entities(AuditLog.action, func.count(AuditLog.id).label("total"))
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(5)
        .all()
    )
    top_atores_raw = (
        q.with_entities(AuditLog.actor_id, func.count(AuditLog.id).label("total"))
        .filter(AuditLog.actor_id.isnot(None))
        .group_by(AuditLog.actor_id)
        .order_by(func.count(AuditLog.id).desc())
        .limit(5)
        .all()
    )
    volume_diario_raw = (
        q.with_entities(func.date(AuditLog.criado_em).label("dia"), func.count(AuditLog.id).label("total"))
        .group_by(func.date(AuditLog.criado_em))
        .order_by(func.date(AuditLog.criado_em).desc())
        .limit(7)
        .all()
    )
    volume_diario_raw = list(reversed(volume_diario_raw))

    return {
        "total_eventos": total_eventos,
        "top_acoes": [{"chave": a[0], "total": int(a[1])} for a in top_acoes_raw if a[0]],
        "top_atores": [{"chave": str(a[0]), "total": int(a[1])} for a in top_atores_raw if a[0] is not None],
        "volume_diario": [{"dia": str(v[0]), "total": int(v[1])} for v in volume_diario_raw],
    }
