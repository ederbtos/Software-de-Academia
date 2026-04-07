from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, create_access_token, verify_password
from app.db.database import get_db, engine, Base, get_tenant_db
from app.models.public import UsuarioPublic, UsuarioPublicRole, Academia
from app.models import tenant as _  # noqa: F401 — registra models tenant no metadata
from app.routers import public as public_router
from app.routers import tenant as tenant_router
from app.core.deps import (
    get_schema_from_request, get_tenant_session,
    get_current_funcionario, require_superadmin, get_current_user_public,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria tabelas do schema public ao iniciar
    from app.models.public import Base as PublicBase  # noqa
    Base.metadata.create_all(bind=engine)
    _seed_superadmin()
    yield


def _seed_superadmin():
    db = next(get_db())
    try:
        exists = db.query(UsuarioPublic).filter(
            UsuarioPublic.email == settings.superadmin_email
        ).first()
        if not exists:
            admin = UsuarioPublic(
                nome="Superadmin",
                email=settings.superadmin_email,
                senha_hash=hash_password(settings.superadmin_password),
                role=UsuarioPublicRole.superadmin,
                ativo=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


app = FastAPI(title="Academia System", version="1.0.0", lifespan=lifespan)

templates = Jinja2Templates(directory="app/templates")

# Monta arquivos estáticos se a pasta existir
import os
if os.path.isdir("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Registra routers da API
app.include_router(public_router.router, prefix="/api/v1", tags=["public"])
app.include_router(tenant_router.router, prefix="/api/v1", tags=["tenant"])


# ---------------------------------------------------------------------------
# Rotas HTML — Login / Logout
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    token = request.cookies.get("access_token")
    if token:
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/auth/login/form")
async def login_form(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Tenta login público (superadmin / admin academia)
    user = db.query(UsuarioPublic).filter(UsuarioPublic.email == email).first()
    if user and verify_password(password, user.senha_hash) and user.ativo:
        token = create_access_token({"sub": user.id, "scope": "public", "role": user.role.value})
        redirect_url = "/superadmin" if user.role == UsuarioPublicRole.superadmin else "/dashboard"
        resp = RedirectResponse(redirect_url, status_code=302)
        resp.set_cookie("access_token", token, httponly=True, samesite="lax")
        return resp

    # Tenta login como funcionário de tenant (a partir do subdomínio)
    host = request.headers.get("host", "")
    slug = host.split(".")[0]
    academia = db.query(Academia).filter(Academia.slug == slug).first()
    if academia:
        tenant_db = next(get_tenant_db(academia.schema_name))
        try:
            from app.models.tenant import Funcionario
            from sqlalchemy import text
            tenant_db.execute(text(f'SET search_path TO "{academia.schema_name}", public'))
            func = tenant_db.query(Funcionario).filter(Funcionario.email == email).first()
            if func and verify_password(password, func.senha_hash) and func.ativo:
                token = create_access_token({"sub": func.id, "scope": "tenant", "role": func.role.value})
                resp = RedirectResponse("/dashboard", status_code=302)
                resp.set_cookie("access_token", token, httponly=True, samesite="lax")
                return resp
        finally:
            tenant_db.close()

    return RedirectResponse("/login?error=Credenciais+inválidas", status_code=302)


@app.get("/auth/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


# ---------------------------------------------------------------------------
# Rotas HTML — Tenant (Academia)
# ---------------------------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    db: Session = Depends(get_tenant_session),
    func=Depends(get_current_funcionario),
):
    from app.services.relatorio import get_dashboard
    stats = get_dashboard(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats, "func": func})


@app.get("/alunos", response_class=HTMLResponse)
def alunos_page(
    request: Request,
    db: Session = Depends(get_tenant_session),
    _=Depends(get_current_funcionario),
):
    from app.services.aluno import listar_alunos
    alunos = listar_alunos(db, apenas_ativos=False)
    return templates.TemplateResponse("alunos.html", {"request": request, "alunos": alunos})


@app.post("/alunos")
async def criar_aluno_form(
    request: Request,
    nome: str = Form(...),
    email: str = Form(None),
    cpf: str = Form(None),
    telefone: str = Form(None),
    data_nascimento: str = Form(None),
    sexo: str = Form(None),
    endereco: str = Form(None),
    observacoes: str = Form(None),
    db: Session = Depends(get_tenant_session),
    _=Depends(get_current_funcionario),
):
    from app.schemas.tenant import AlunoCreate
    from app.services.aluno import criar_aluno, listar_alunos
    from datetime import date
    try:
        dn = date.fromisoformat(data_nascimento) if data_nascimento else None
        data = AlunoCreate(nome=nome, email=email or None, cpf=cpf or None, telefone=telefone or None,
                           data_nascimento=dn, sexo=sexo or None, endereco=endereco or None,
                           observacoes=observacoes or None)
        criar_aluno(data, db)
        alunos = listar_alunos(db, apenas_ativos=False)
        return templates.TemplateResponse("alunos.html", {"request": request, "alunos": alunos, "success": "Aluno cadastrado com sucesso!"})
    except Exception as e:
        alunos = listar_alunos(db, apenas_ativos=False)
        return templates.TemplateResponse("alunos.html", {"request": request, "alunos": alunos, "error": str(e)})


# ---------------------------------------------------------------------------
# Rotas HTML — Superadmin
# ---------------------------------------------------------------------------

@app.get("/superadmin", response_class=HTMLResponse)
def superadmin_page(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    from app.services.academia import listar_academias
    academias = listar_academias(db)
    return templates.TemplateResponse("superadmin.html", {"request": request, "academias": academias})


@app.post("/superadmin/academias/form")
async def criar_academia_form(
    request: Request,
    nome: str = Form(...),
    slug: str = Form(...),
    cnpj: str = Form(None),
    telefone: str = Form(None),
    email: str = Form(None),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    from app.schemas.public import AcademiaCreate
    from app.services.academia import criar_academia, listar_academias
    try:
        data = AcademiaCreate(nome=nome, slug=slug, cnpj=cnpj or None, telefone=telefone or None, email=email or None)
        criar_academia(data, db)
        academias = listar_academias(db)
        return templates.TemplateResponse("superadmin.html", {"request": request, "academias": academias, "success": f"Academia '{nome}' criada!"})
    except Exception as e:
        academias = listar_academias(db)
        return templates.TemplateResponse("superadmin.html", {"request": request, "academias": academias, "error": str(e)})
