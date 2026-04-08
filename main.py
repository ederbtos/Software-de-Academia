from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import http_exception_handler
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, create_access_token, verify_password
from app.db.database import get_db, engine, Base, get_tenant_db
from app.models.public import UsuarioPublic, UsuarioPublicRole, Academia
from app.models import tenant as _  # noqa: F401
from app.routers import public as public_router
from app.routers import tenant as tenant_router
from app.core.deps import (
    get_tenant_session,
    get_current_funcionario,
    require_superadmin,
    require_admin,
    require_professor_or_admin,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_superadmin()
    from app.core.scheduler import criar_scheduler
    scheduler = criar_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


def _seed_superadmin():
    db = next(get_db())
    try:
        exists = db.query(UsuarioPublic).filter(
            UsuarioPublic.email == settings.superadmin_email
        ).first()
        if not exists:
            db.add(UsuarioPublic(
                nome="Superadmin",
                email=settings.superadmin_email,
                senha_hash=hash_password(settings.superadmin_password),
                role=UsuarioPublicRole.superadmin,
                ativo=True,
            ))
            db.commit()
    finally:
        db.close()


app = FastAPI(title="Academia System", version="1.0.0", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")

import os
if os.path.isdir("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(public_router.router, prefix="/api/v1", tags=["public"])
app.include_router(tenant_router.router, prefix="/api/v1", tags=["tenant"])


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def page_not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return await http_exception_handler(request, exc)
    return templates.TemplateResponse(request, "404.html", status_code=404)


@app.exception_handler(500)
async def internal_error(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return await http_exception_handler(request, exc)
    return templates.TemplateResponse(request, "500.html", status_code=500)


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return RedirectResponse("/dashboard" if request.cookies.get("access_token") else "/login")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = None, success: str = None):
    return templates.TemplateResponse(request, "login.html", {"error": error, "success": success})


@app.post("/auth/login/form")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    slug: str = Form(None),
    db: Session = Depends(get_db),
):
    user = db.query(UsuarioPublic).filter(UsuarioPublic.email == email).first()
    if user and verify_password(password, user.senha_hash) and user.ativo:
        token = create_access_token({"sub": user.id, "scope": "public", "role": user.role.value})
        dest = "/superadmin" if user.role == UsuarioPublicRole.superadmin else "/dashboard"
        resp = RedirectResponse(dest, status_code=302)
        resp.set_cookie("access_token", token, httponly=True, samesite="lax")
        return resp

    # Resolve a academia: slug do subdomínio tem prioridade, campo do form é fallback (dev/localhost)
    host = request.headers.get("host", "")
    host_slug = host.split(".")[0]
    resolved_slug = None if host_slug in ("localhost", "127", "127.0.0.1", "") else host_slug
    resolved_slug = resolved_slug or slug

    if resolved_slug:
        academia = db.query(Academia).filter(Academia.slug == resolved_slug).first()
        if academia:
            tenant_db = next(get_tenant_db(academia.schema_name))
            try:
                from app.models.tenant import Funcionario
                func = tenant_db.query(Funcionario).filter(Funcionario.email == email).first()
                if func and verify_password(password, func.senha_hash) and func.ativo:
                    token = create_access_token({
                        "sub": func.id,
                        "scope": "tenant",
                        "role": func.role.value,
                        "schema": academia.schema_name,
                    })
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
# Recuperação de senha
# ---------------------------------------------------------------------------

@app.get("/auth/esqueci-senha", response_class=HTMLResponse)
def esqueci_senha_page(request: Request):
    return templates.TemplateResponse(request, "esqueci_senha.html", {})


@app.post("/auth/esqueci-senha")
async def esqueci_senha_form(
    request: Request,
    email: str = Form(...),
    slug: str = Form(None),
    db: Session = Depends(get_db),
):
    import secrets
    from datetime import timedelta
    from app.models.public import PasswordResetToken

    # Verifica se o e-mail existe (público ou tenant)
    schema_name = None
    user_email = None

    if slug:
        academia = db.query(Academia).filter(Academia.slug == slug).first()
        if academia:
            tenant_db = next(get_tenant_db(academia.schema_name))
            try:
                from app.models.tenant import Funcionario
                func = tenant_db.query(Funcionario).filter(Funcionario.email == email).first()
                if func:
                    schema_name = academia.schema_name
                    user_email = email
            finally:
                tenant_db.close()
    else:
        user = db.query(UsuarioPublic).filter(UsuarioPublic.email == email).first()
        if user:
            user_email = email

    if not user_email:
        return templates.TemplateResponse(request, "esqueci_senha.html",
            {"error": "E-mail não encontrado."})

    token_str = secrets.token_hex(32)
    expira = __import__("datetime").datetime.utcnow() + timedelta(hours=2)
    db.add(PasswordResetToken(token=token_str, email=user_email,
                               schema_name=schema_name, expira_em=expira))
    db.commit()

    link = f"{request.base_url}auth/redefinir-senha?token={token_str}"

    # Tenta enviar e-mail
    from app.services.notificacao import enviar_email
    enviado = enviar_email(user_email, "Recuperação de Senha — AcademiaSys",
        f"<p>Clique no link abaixo para redefinir sua senha (válido por 2h):</p>"
        f"<p><a href='{link}'>{link}</a></p>")

    ctx = {"success": f"Se o e-mail existir, você receberá um link em breve."}
    if not enviado:
        ctx["dev_link"] = link  # exibe em dev se SMTP não configurado
    return templates.TemplateResponse(request, "esqueci_senha.html", ctx)


@app.get("/auth/redefinir-senha", response_class=HTMLResponse)
def redefinir_senha_page(request: Request, token: str, db: Session = Depends(get_db)):
    from datetime import datetime
    from app.models.public import PasswordResetToken
    rec = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.usado == False,
        PasswordResetToken.expira_em > datetime.utcnow(),
    ).first()
    if not rec:
        return templates.TemplateResponse(request, "redefinir_senha.html",
            {"error": "Link inválido ou expirado."})
    return templates.TemplateResponse(request, "redefinir_senha.html", {"token": token})


@app.post("/auth/redefinir-senha")
async def redefinir_senha_form(
    request: Request,
    token: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_senha: str = Form(...),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    from app.models.public import PasswordResetToken

    if nova_senha != confirmar_senha:
        return templates.TemplateResponse(request, "redefinir_senha.html",
            {"token": token, "error": "As senhas não coincidem."})

    rec = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.usado == False,
        PasswordResetToken.expira_em > datetime.utcnow(),
    ).first()

    if not rec:
        return templates.TemplateResponse(request, "redefinir_senha.html",
            {"error": "Link inválido ou expirado."})

    nova_hash = hash_password(nova_senha)

    if rec.schema_name:
        tenant_db = next(get_tenant_db(rec.schema_name))
        try:
            from app.models.tenant import Funcionario
            func = tenant_db.query(Funcionario).filter(Funcionario.email == rec.email).first()
            if func:
                func.senha_hash = nova_hash
                tenant_db.commit()
        finally:
            tenant_db.close()
    else:
        user = db.query(UsuarioPublic).filter(UsuarioPublic.email == rec.email).first()
        if user:
            user.senha_hash = nova_hash

    rec.usado = True
    db.commit()
    return RedirectResponse("/login?success=Senha+redefinida+com+sucesso", status_code=302)


# ---------------------------------------------------------------------------
# Perfil do funcionário
# ---------------------------------------------------------------------------

@app.get("/perfil", response_class=HTMLResponse)
def perfil_page(request: Request, db: Session = Depends(get_tenant_session),
                current_user=Depends(get_current_funcionario)):
    return templates.TemplateResponse(request, "perfil.html", {"func": current_user})


@app.post("/perfil/editar")
async def perfil_editar_form(
    request: Request,
    nome: str = Form(...),
    telefone: str = Form(None),
    db: Session = Depends(get_tenant_session),
    current_user=Depends(get_current_funcionario),
):
    from app.models.tenant import Funcionario
    f = db.query(Funcionario).filter(Funcionario.id == current_user.id).first()
    if f:
        f.nome = nome
        f.telefone = telefone or None
        db.commit()
    return templates.TemplateResponse(request, "perfil.html",
        {"func": f or current_user, "success": "Perfil atualizado!"})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_tenant_session), current_user=Depends(get_current_funcionario)):
    from app.services.relatorio import get_dashboard
    return templates.TemplateResponse(request, "dashboard.html", {"stats": get_dashboard(db), "func": current_user})


# ---------------------------------------------------------------------------
# Alunos
# ---------------------------------------------------------------------------

@app.get("/alunos", response_class=HTMLResponse)
def alunos_page(request: Request, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.services.aluno import listar_alunos
    return templates.TemplateResponse(request, "alunos.html", {"alunos": listar_alunos(db, False)})


@app.post("/alunos")
async def criar_aluno_form(
    request: Request,
    nome: str = Form(...), email: str = Form(None), cpf: str = Form(None),
    telefone: str = Form(None), data_nascimento: str = Form(None), sexo: str = Form(None),
    endereco: str = Form(None), observacoes: str = Form(None),
    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario),
):
    from app.schemas.tenant import AlunoCreate
    from app.services.aluno import criar_aluno, listar_alunos
    try:
        dn = date.fromisoformat(data_nascimento) if data_nascimento else None
        criar_aluno(AlunoCreate(nome=nome, email=email or None, cpf=cpf or None, telefone=telefone or None,
                                data_nascimento=dn, sexo=sexo or None, endereco=endereco or None,
                                observacoes=observacoes or None), db)
        return templates.TemplateResponse(request, "alunos.html", {"alunos": listar_alunos(db, False), "success": "Aluno cadastrado!"})
    except Exception as e:
        return templates.TemplateResponse(request, "alunos.html", {"alunos": listar_alunos(db, False), "error": str(e)})


@app.get("/alunos/{aluno_id}", response_class=HTMLResponse)
def aluno_detalhe_page(request: Request, aluno_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.services.aluno import buscar_aluno
    from app.services.treino import listar_treinos_aluno, listar_presencas_aluno, listar_avaliacoes_aluno
    from app.models.tenant import Matricula, Pagamento, Plano, MatriculaStatus

    aluno = buscar_aluno(aluno_id, db)
    planos = db.query(Plano).filter(Plano.ativo == True).all()
    matricula_ativa = (db.query(Matricula)
        .filter(Matricula.aluno_id == aluno_id, Matricula.status == MatriculaStatus.ativa)
        .order_by(Matricula.data_vencimento.desc()).first())
    ultimo_pagamento = None
    if matricula_ativa:
        ultimo_pagamento = (db.query(Pagamento)
            .filter(Pagamento.matricula_id == matricula_ativa.id)
            .order_by(Pagamento.data_vencimento.desc()).first())

    return templates.TemplateResponse(request, "aluno_detalhe.html", {
        "aluno": aluno,
        "treinos": listar_treinos_aluno(aluno_id, db),
        "presencas": listar_presencas_aluno(aluno_id, db)[:30],
        "avaliacoes": listar_avaliacoes_aluno(aluno_id, db),
        "planos": planos, "matricula_ativa": matricula_ativa,
        "ultimo_pagamento": ultimo_pagamento, "hoje": date.today().isoformat(),
    })


@app.post("/alunos/{aluno_id}/editar")
async def editar_aluno_form(
    request: Request, aluno_id: int,
    nome: str = Form(...), email: str = Form(None), telefone: str = Form(None),
    data_nascimento: str = Form(None), sexo: str = Form(None),
    endereco: str = Form(None), observacoes: str = Form(None), ativo: str = Form("1"),
    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario),
):
    from app.schemas.tenant import AlunoUpdate
    from app.services.aluno import atualizar_aluno
    try:
        dn = date.fromisoformat(data_nascimento) if data_nascimento else None
        atualizar_aluno(aluno_id, AlunoUpdate(nome=nome, email=email or None, telefone=telefone or None,
            data_nascimento=dn, sexo=sexo or None, endereco=endereco or None,
            observacoes=observacoes or None, ativo=ativo == "1"), db)
    except Exception:
        pass
    return RedirectResponse(f"/alunos/{aluno_id}", status_code=302)


# ---------------------------------------------------------------------------
# Check-in
# ---------------------------------------------------------------------------

@app.get("/checkin", response_class=HTMLResponse)
def checkin_page(request: Request, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.models.tenant import Presenca
    from sqlalchemy.orm import joinedload
    presencas_hoje = (db.query(Presenca)
        .options(joinedload(Presenca.aluno))
        .filter(Presenca.data_hora >= date.today().strftime("%Y-%m-%d"))
        .order_by(Presenca.data_hora.desc()).all())
    return templates.TemplateResponse(request, "checkin.html", {"presencas_hoje": presencas_hoje})


@app.post("/checkin")
async def checkin_form(
    request: Request,
    busca: str = Form(None), acao: str = Form("buscar"),
    aluno_id: str = Form(None), observacoes: str = Form(None),
    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario),
):
    from app.models.tenant import Presenca, Aluno
    from sqlalchemy.orm import joinedload
    from sqlalchemy import or_

    ctx = {}
    if acao == "registrar" and aluno_id:
        try:
            from app.services.treino import registrar_presenca
            from app.schemas.tenant import PresencaCreate
            registrar_presenca(PresencaCreate(aluno_id=int(aluno_id), observacoes=observacoes or None), db)
            ctx["success"] = "Check-in registrado!"
        except Exception as e:
            ctx["error"] = str(e)
    elif acao == "buscar" and busca:
        ctx["busca"] = busca
        ctx["alunos_encontrados"] = (db.query(Aluno)
            .filter(Aluno.ativo == True, or_(
                Aluno.nome.ilike(f"%{busca}%"),
                Aluno.cpf.ilike(f"%{busca}%"),
            )).all())

    presencas_hoje = (db.query(Presenca)
        .options(joinedload(Presenca.aluno))
        .filter(Presenca.data_hora >= date.today().strftime("%Y-%m-%d"))
        .order_by(Presenca.data_hora.desc()).all())
    ctx.update({"presencas_hoje": presencas_hoje})
    return templates.TemplateResponse(request, "checkin.html", ctx)


# ---------------------------------------------------------------------------
# Matrículas / Pagamentos
# ---------------------------------------------------------------------------

@app.get("/matriculas", response_class=HTMLResponse)
def matriculas_page(request: Request, busca: str = None, status: str = None,
                    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.models.tenant import Matricula, Pagamento, Aluno, MatriculaStatus
    from sqlalchemy.orm import joinedload

    q = db.query(Matricula).options(joinedload(Matricula.plano), joinedload(Matricula.aluno))
    if status:
        q = q.filter(Matricula.status == MatriculaStatus(status))
    if busca:
        q = q.join(Aluno).filter(Aluno.nome.ilike(f"%{busca}%"))

    rows = []
    for m in q.order_by(Matricula.data_vencimento.desc()).all():
        pag = (db.query(Pagamento).filter(Pagamento.matricula_id == m.id)
               .order_by(Pagamento.data_vencimento.desc()).first())
        rows.append({"matricula": m, "aluno_nome": m.aluno.nome if m.aluno else "—", "ultimo_pag": pag})

    return templates.TemplateResponse(request, "matriculas.html", {
        "matriculas": rows,
        "busca": busca, "status_filtro": status, "hoje": date.today(),
    })


@app.post("/matriculas")
async def criar_matricula_form(
    request: Request,
    aluno_id: int = Form(...), plano_id: int = Form(...),
    data_inicio: str = Form(...), observacoes: str = Form(None),
    redirect_url: str = Form("/matriculas"),
    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario),
):
    from app.schemas.tenant import MatriculaCreate
    from app.services.aluno import matricular_aluno
    try:
        matricular_aluno(MatriculaCreate(aluno_id=aluno_id, plano_id=plano_id,
            data_inicio=date.fromisoformat(data_inicio), observacoes=observacoes or None), db)
    except Exception:
        pass
    return RedirectResponse(redirect_url, status_code=302)


@app.post("/matriculas/{matricula_id}/renovar")
async def renovar_matricula_form(matricula_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.services.aluno import renovar_matricula
    try:
        renovar_matricula(matricula_id, db)
    except Exception:
        pass
    return RedirectResponse("/matriculas", status_code=302)


@app.post("/pagamentos/pagar")
async def registrar_pagamento_form(
    request: Request,
    pagamento_id: int = Form(...), metodo: str = Form(...),
    data_pagamento: str = Form(None), observacoes: str = Form(None),
    redirect_url: str = Form("/matriculas"),
    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario),
):
    from app.schemas.tenant import PagamentoRegistrar, PagamentoMetodo
    from app.services.aluno import registrar_pagamento
    try:
        dp = date.fromisoformat(data_pagamento) if data_pagamento else None
        registrar_pagamento(pagamento_id, PagamentoRegistrar(
            metodo=PagamentoMetodo(metodo), data_pagamento=dp, observacoes=observacoes or None), db)
    except Exception:
        pass
    return RedirectResponse(redirect_url, status_code=302)


# ---------------------------------------------------------------------------
# Planos
# ---------------------------------------------------------------------------

@app.get("/planos", response_class=HTMLResponse)
def planos_page(request: Request, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.models.tenant import Plano
    return templates.TemplateResponse(request, "planos.html", {
        "planos": db.query(Plano).order_by(Plano.nome).all()
    })


@app.post("/planos")
async def criar_plano_form(
    request: Request,
    nome: str = Form(...), descricao: str = Form(None),
    valor: str = Form(...), duracao_dias: int = Form(30),
    db: Session = Depends(get_tenant_session), _=Depends(require_admin),
):
    from app.models.tenant import Plano
    from decimal import Decimal
    success = error = None
    try:
        db.add(Plano(nome=nome, descricao=descricao or None, valor=Decimal(valor), duracao_dias=duracao_dias))
        db.commit()
        success = f"Plano '{nome}' criado!"
    except Exception as e:
        error = str(e)
    return templates.TemplateResponse(request, "planos.html", {
        "planos": db.query(Plano).order_by(Plano.nome).all(),
        "success": success, "error": error,
    })


@app.post("/planos/editar")
async def editar_plano_form(
    plano_id: int = Form(...), nome: str = Form(...), descricao: str = Form(None),
    valor: str = Form(...), duracao_dias: int = Form(30),
    db: Session = Depends(get_tenant_session), _=Depends(require_admin),
):
    from app.models.tenant import Plano
    from decimal import Decimal
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if plano:
        plano.nome = nome; plano.descricao = descricao or None
        plano.valor = Decimal(valor); plano.duracao_dias = duracao_dias
        db.commit()
    return RedirectResponse("/planos", status_code=302)


@app.post("/planos/{plano_id}/ativar")
async def ativar_plano(plano_id: int, db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    from app.models.tenant import Plano
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if plano: plano.ativo = True; db.commit()
    return RedirectResponse("/planos", status_code=302)


@app.post("/planos/{plano_id}/desativar")
async def desativar_plano(plano_id: int, db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    from app.models.tenant import Plano
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if plano: plano.ativo = False; db.commit()
    return RedirectResponse("/planos", status_code=302)


# ---------------------------------------------------------------------------
# Treinos
# ---------------------------------------------------------------------------

@app.get("/treinos", response_class=HTMLResponse)
def treinos_page(request: Request, busca_aluno: str = None,
                 db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.models.tenant import Treino, Aluno
    from sqlalchemy.orm import joinedload
    q = db.query(Treino).options(joinedload(Treino.aluno), joinedload(Treino.exercicios))
    if busca_aluno:
        q = q.join(Aluno).filter(Aluno.nome.ilike(f"%{busca_aluno}%"))
    return templates.TemplateResponse(request, "treinos.html", {
        "treinos": q.order_by(Treino.id.desc()).all(),
        "busca_aluno": busca_aluno, "hoje": date.today(),
    })


@app.get("/treinos/novo", response_class=HTMLResponse)
def treino_novo_page(request: Request, aluno_id: str = None,
                     db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.services.treino import listar_exercicios
    from app.services.aluno import listar_alunos
    from app.models.tenant import Funcionario, FuncionarioRole
    professores = db.query(Funcionario).filter(
        Funcionario.role.in_([FuncionarioRole.professor, FuncionarioRole.admin]),
        Funcionario.ativo == True).all()
    return templates.TemplateResponse(request, "treino_novo.html", {
        "alunos": listar_alunos(db),
        "exercicios": listar_exercicios(db), "professores": professores,
        "aluno_id": aluno_id, "hoje": date.today().isoformat(),
    })


@app.post("/treinos")
async def criar_treino_form(request: Request, db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.schemas.tenant import TreinoCreate, TreinoExercicioCreate
    from app.services.treino import criar_treino, listar_exercicios
    from app.services.aluno import listar_alunos
    from app.models.tenant import Funcionario, FuncionarioRole
    form = await request.form()
    try:
        exercicios = []
        idx = 1
        while f"exercicios[{idx}][exercicio_id]" in form:
            exercicios.append(TreinoExercicioCreate(
                exercicio_id=int(form[f"exercicios[{idx}][exercicio_id]"]),
                series=int(form.get(f"exercicios[{idx}][series]", 3)),
                repeticoes=int(form.get(f"exercicios[{idx}][repeticoes]", 12)),
                carga_kg=form.get(f"exercicios[{idx}][carga_kg]") or None,
                descanso_segundos=int(form.get(f"exercicios[{idx}][descanso_segundos]", 60)),
                observacoes=form.get(f"exercicios[{idx}][observacoes]") or None,
                ordem=idx,
            ))
            idx += 1
        treino = criar_treino(TreinoCreate(
            aluno_id=int(form["aluno_id"]),
            professor_id=int(form["professor_id"]) if form.get("professor_id") else None,
            identificador=form.get("identificador", "A"),
            nome=form.get("nome") or None, objetivo=form.get("objetivo") or None,
            data_inicio=date.fromisoformat(form["data_inicio"]) if form.get("data_inicio") else None,
            data_validade=date.fromisoformat(form["data_validade"]) if form.get("data_validade") else None,
            exercicios=exercicios,
        ), db)
        return RedirectResponse(f"/treinos/{treino.id}", status_code=302)
    except Exception as e:
        professores = db.query(Funcionario).filter(
            Funcionario.role.in_([FuncionarioRole.professor, FuncionarioRole.admin])).all()
        return templates.TemplateResponse(request, "treino_novo.html", {
            "error": str(e), "alunos": listar_alunos(db),
            "exercicios": listar_exercicios(db), "professores": professores,
            "aluno_id": form.get("aluno_id"), "hoje": date.today().isoformat(),
        })


@app.get("/treinos/{treino_id}", response_class=HTMLResponse)
def treino_detalhe_page(request: Request, treino_id: int,
                        db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.services.treino import buscar_treino
    return templates.TemplateResponse(request, "treino_detalhe.html", {
        "treino": buscar_treino(treino_id, db), "hoje": date.today(),
    })


@app.get("/treinos/{treino_id}/editar", response_class=HTMLResponse)
def treino_editar_page(request: Request, treino_id: int,
                       db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.services.treino import buscar_treino, listar_exercicios
    from app.services.aluno import listar_alunos
    from app.models.tenant import Funcionario, FuncionarioRole
    professores = db.query(Funcionario).filter(
        Funcionario.role.in_([FuncionarioRole.professor, FuncionarioRole.admin]),
        Funcionario.ativo == True).all()
    return templates.TemplateResponse(request, "treino_editar.html", {
        "treino": buscar_treino(treino_id, db),
        "alunos": listar_alunos(db),
        "exercicios": listar_exercicios(db),
        "professores": professores,
    })


@app.post("/treinos/{treino_id}/editar")
async def editar_treino_form(request: Request, treino_id: int,
                              db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.services.treino import atualizar_treino, listar_exercicios
    from app.services.aluno import listar_alunos
    from app.models.tenant import Funcionario, FuncionarioRole
    form = await request.form()
    try:
        exercicios = []
        idx = 1
        while f"exercicios[{idx}][exercicio_id]" in form:
            exercicios.append({
                "exercicio_id": int(form[f"exercicios[{idx}][exercicio_id]"]),
                "series": int(form.get(f"exercicios[{idx}][series]", 3)),
                "repeticoes": int(form.get(f"exercicios[{idx}][repeticoes]", 12)),
                "carga_kg": form.get(f"exercicios[{idx}][carga_kg]") or None,
                "descanso_segundos": int(form.get(f"exercicios[{idx}][descanso_segundos]", 60)),
                "observacoes": form.get(f"exercicios[{idx}][observacoes]") or None,
                "ordem": idx,
            })
            idx += 1
        treino_data = {
            "aluno_id": int(form["aluno_id"]),
            "professor_id": int(form["professor_id"]) if form.get("professor_id") else None,
            "identificador": form.get("identificador", "A"),
            "nome": form.get("nome") or None,
            "objetivo": form.get("objetivo") or None,
            "data_inicio": date.fromisoformat(form["data_inicio"]) if form.get("data_inicio") else None,
            "data_validade": date.fromisoformat(form["data_validade"]) if form.get("data_validade") else None,
        }
        atualizar_treino(treino_id, treino_data, exercicios, db)
        return RedirectResponse(f"/treinos/{treino_id}", status_code=302)
    except Exception as e:
        from app.services.treino import buscar_treino
        professores = db.query(Funcionario).filter(
            Funcionario.role.in_([FuncionarioRole.professor, FuncionarioRole.admin])).all()
        return templates.TemplateResponse(request, "treino_editar.html", {
            "treino": buscar_treino(treino_id, db), "error": str(e),
            "alunos": listar_alunos(db), "exercicios": listar_exercicios(db),
            "professores": professores,
        })


@app.post("/treinos/{treino_id}/desativar")
async def desativar_treino_form(treino_id: int,
                                 db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.services.treino import desativar_treino
    try:
        t = desativar_treino(treino_id, db)
        return RedirectResponse(f"/alunos/{t.aluno_id}", status_code=302)
    except Exception:
        return RedirectResponse("/treinos", status_code=302)


# ---------------------------------------------------------------------------
# Avaliações Físicas
# ---------------------------------------------------------------------------

@app.get("/avaliacoes", response_class=HTMLResponse)
def avaliacoes_page(request: Request, busca: str = None,
                    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.models.tenant import AvaliacaoFisica, Aluno
    q = db.query(AvaliacaoFisica, Aluno).join(Aluno, Aluno.id == AvaliacaoFisica.aluno_id)
    if busca:
        q = q.filter(Aluno.nome.ilike(f"%{busca}%"))
    rows = [{"av": av, "aluno_nome": aluno.nome} for av, aluno in q.order_by(AvaliacaoFisica.data.desc()).all()]
    return templates.TemplateResponse(request, "avaliacoes.html", {"avaliacoes": rows, "busca": busca})


@app.get("/avaliacoes/nova", response_class=HTMLResponse)
def avaliacao_nova_page(request: Request, aluno_id: str = None,
                        db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.services.aluno import listar_alunos
    return templates.TemplateResponse(request, "avaliacao_nova.html", {
        "alunos": listar_alunos(db),
        "aluno_id": aluno_id, "hoje": date.today().isoformat(),
    })


@app.get("/avaliacoes/{av_id}", response_class=HTMLResponse)
def avaliacao_detalhe_page(request: Request, av_id: int,
                            db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.models.tenant import AvaliacaoFisica, Aluno
    av = db.query(AvaliacaoFisica).filter(AvaliacaoFisica.id == av_id).first()
    if not av:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    aluno = db.query(Aluno).filter(Aluno.id == av.aluno_id).first()
    return templates.TemplateResponse(request, "avaliacao_detalhe.html", {
        "avaliacao": av, "aluno_nome": aluno.nome if aluno else "—",
    })


@app.post("/avaliacoes")
async def criar_avaliacao_form(request: Request, db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.schemas.tenant import AvaliacaoCreate
    from app.services.treino import criar_avaliacao
    from app.services.aluno import listar_alunos
    from decimal import Decimal

    def _d(v): return Decimal(v) if v else None
    form = await request.form()
    try:
        av = criar_avaliacao(AvaliacaoCreate(
            aluno_id=int(form["aluno_id"]), data=date.fromisoformat(form["data"]),
            peso_kg=_d(form.get("peso_kg")), altura_cm=_d(form.get("altura_cm")),
            gordura_percent=_d(form.get("gordura_percent")), massa_muscular_kg=_d(form.get("massa_muscular_kg")),
            torax=_d(form.get("torax")), cintura=_d(form.get("cintura")), quadril=_d(form.get("quadril")),
            braco_dir=_d(form.get("braco_dir")), braco_esq=_d(form.get("braco_esq")),
            coxa_dir=_d(form.get("coxa_dir")), coxa_esq=_d(form.get("coxa_esq")),
            panturrilha_dir=_d(form.get("panturrilha_dir")), panturrilha_esq=_d(form.get("panturrilha_esq")),
            observacoes=form.get("observacoes") or None,
        ), db)
        return RedirectResponse(f"/alunos/{av.aluno_id}#tabAvaliacoes", status_code=302)
    except Exception as e:
        return templates.TemplateResponse(request, "avaliacao_nova.html", {
            "error": str(e), "alunos": listar_alunos(db),
            "aluno_id": form.get("aluno_id"), "hoje": date.today().isoformat(),
        })


@app.post("/avaliacoes/{av_id}/editar")
async def editar_avaliacao_form(
    request: Request, av_id: int,
    db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin),
):
    from app.models.tenant import AvaliacaoFisica
    from decimal import Decimal
    from app.services.treino import calcular_imc

    def _d(v): return Decimal(v) if v else None
    form = await request.form()
    av = db.query(AvaliacaoFisica).filter(AvaliacaoFisica.id == av_id).first()
    if av:
        av.data = date.fromisoformat(form["data"])
        av.peso_kg = _d(form.get("peso_kg"))
        av.altura_cm = _d(form.get("altura_cm"))
        av.gordura_percent = _d(form.get("gordura_percent"))
        av.massa_muscular_kg = _d(form.get("massa_muscular_kg"))
        av.torax = _d(form.get("torax"))
        av.cintura = _d(form.get("cintura"))
        av.quadril = _d(form.get("quadril"))
        av.braco_dir = _d(form.get("braco_dir"))
        av.braco_esq = _d(form.get("braco_esq"))
        av.coxa_dir = _d(form.get("coxa_dir"))
        av.coxa_esq = _d(form.get("coxa_esq"))
        av.panturrilha_dir = _d(form.get("panturrilha_dir"))
        av.panturrilha_esq = _d(form.get("panturrilha_esq"))
        av.observacoes = form.get("observacoes") or None
        if av.peso_kg and av.altura_cm:
            av.imc = round(float(av.peso_kg) / ((float(av.altura_cm) / 100) ** 2), 1)
        db.commit()
    return RedirectResponse(f"/avaliacoes/{av_id}", status_code=302)


@app.post("/avaliacoes/{av_id}/deletar")
async def deletar_avaliacao_form(
    av_id: int, db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin),
):
    from app.models.tenant import AvaliacaoFisica
    av = db.query(AvaliacaoFisica).filter(AvaliacaoFisica.id == av_id).first()
    aluno_id = av.aluno_id if av else None
    if av:
        db.delete(av)
        db.commit()
    return RedirectResponse(f"/alunos/{aluno_id}#tabAvaliacoes" if aluno_id else "/avaliacoes", status_code=302)


# ---------------------------------------------------------------------------
# Aulas Coletivas
# ---------------------------------------------------------------------------

@app.get("/aulas", response_class=HTMLResponse)
def aulas_page(request: Request, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.models.tenant import Aula, InscricaoAula, InscricaoStatus, Funcionario, Aluno
    from sqlalchemy import func as sqlfunc
    from sqlalchemy.orm import joinedload

    aulas = db.query(Aula).options(joinedload(Aula.professor)).filter(Aula.ativa == True).all()
    for aula in aulas:
        aula.inscricoes_confirmadas = db.query(sqlfunc.count(InscricaoAula.id)).filter(
            InscricaoAula.aula_id == aula.id, InscricaoAula.status == InscricaoStatus.confirmada).scalar()

    return templates.TemplateResponse(request, "aulas.html", {
        "aulas": aulas,
        "professores": db.query(Funcionario).filter(Funcionario.ativo == True).all(),
        "alunos": db.query(Aluno).filter(Aluno.ativo == True).order_by(Aluno.nome).all(),
    })


@app.post("/aulas")
async def criar_aula_form(
    request: Request,
    nome: str = Form(...), dia_semana: str = Form(...),
    horario_inicio: str = Form(...), horario_fim: str = Form(...),
    professor_id: str = Form(None), capacidade_maxima: int = Form(20),
    db: Session = Depends(get_tenant_session), _=Depends(require_admin),
):
    from app.schemas.tenant import AulaCreate, DiaSemana
    from app.services.aula import criar_aula
    try:
        criar_aula(AulaCreate(nome=nome, professor_id=int(professor_id) if professor_id else None,
            dia_semana=DiaSemana(dia_semana), horario_inicio=horario_inicio,
            horario_fim=horario_fim, capacidade_maxima=capacidade_maxima), db)
    except Exception:
        pass
    return RedirectResponse("/aulas", status_code=302)


@app.post("/aulas/inscrever")
async def inscrever_form(
    aluno_id: int = Form(...), aula_id: int = Form(...),
    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario),
):
    from app.schemas.tenant import InscricaoCreate
    from app.services.aula import inscrever_aluno
    try:
        inscrever_aluno(InscricaoCreate(aluno_id=aluno_id, aula_id=aula_id), db)
    except Exception:
        pass
    return RedirectResponse("/aulas", status_code=302)


@app.post("/aulas/{aula_id}/editar")
async def editar_aula_form(
    aula_id: int,
    nome: str = Form(...), dia_semana: str = Form(...),
    horario_inicio: str = Form(...), horario_fim: str = Form(...),
    professor_id: str = Form(None), capacidade_maxima: int = Form(20),
    db: Session = Depends(get_tenant_session), _=Depends(require_admin),
):
    from app.models.tenant import Aula, DiaSemana
    aula = db.query(Aula).filter(Aula.id == aula_id).first()
    if aula:
        import datetime as dt
        aula.nome = nome
        aula.dia_semana = DiaSemana(dia_semana)
        aula.horario_inicio = dt.time.fromisoformat(horario_inicio)
        aula.horario_fim = dt.time.fromisoformat(horario_fim)
        aula.professor_id = int(professor_id) if professor_id else None
        aula.capacidade_maxima = capacidade_maxima
        db.commit()
    return RedirectResponse("/aulas", status_code=302)


@app.post("/aulas/{aula_id}/desativar")
async def desativar_aula_form(
    aula_id: int, db: Session = Depends(get_tenant_session), _=Depends(require_admin),
):
    from app.models.tenant import Aula
    aula = db.query(Aula).filter(Aula.id == aula_id).first()
    if aula:
        aula.ativa = False
        db.commit()
    return RedirectResponse("/aulas", status_code=302)


@app.post("/inscricoes/{inscricao_id}/cancelar")
async def cancelar_inscricao_form(
    inscricao_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario),
):
    from app.models.tenant import InscricaoAula, InscricaoStatus
    ins = db.query(InscricaoAula).filter(InscricaoAula.id == inscricao_id).first()
    if ins:
        ins.status = InscricaoStatus.cancelada
        db.commit()
    return RedirectResponse("/aulas", status_code=302)


# ---------------------------------------------------------------------------
# Funcionários
# ---------------------------------------------------------------------------

@app.get("/funcionarios", response_class=HTMLResponse)
def funcionarios_page(request: Request, db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    from app.models.tenant import Funcionario
    return templates.TemplateResponse(request, "funcionarios.html", {
        "funcionarios": db.query(Funcionario).order_by(Funcionario.nome).all()
    })


@app.post("/funcionarios")
async def criar_funcionario_form(
    request: Request,
    nome: str = Form(...), email: str = Form(...), password: str = Form(...),
    cpf: str = Form(None), telefone: str = Form(None), role: str = Form("recepcionista"),
    db: Session = Depends(get_tenant_session), _=Depends(require_admin),
):
    from app.models.tenant import Funcionario, FuncionarioRole
    success = error = None
    try:
        db.add(Funcionario(nome=nome, email=email, cpf=cpf or None, telefone=telefone or None,
                           role=FuncionarioRole(role), senha_hash=hash_password(password)))
        db.commit()
        success = "Funcionário criado!"
    except Exception as e:
        error = str(e)
    return templates.TemplateResponse(request, "funcionarios.html", {
        "funcionarios": db.query(Funcionario).order_by(Funcionario.nome).all(),
        "success": success, "error": error,
    })


@app.post("/funcionarios/editar")
async def editar_funcionario_form(
    func_id: int = Form(...), nome: str = Form(...),
    telefone: str = Form(None), role: str = Form("recepcionista"), ativo: str = Form("1"),
    db: Session = Depends(get_tenant_session), _=Depends(require_admin),
):
    from app.models.tenant import Funcionario, FuncionarioRole
    func = db.query(Funcionario).filter(Funcionario.id == func_id).first()
    if func:
        func.nome = nome; func.telefone = telefone or None
        func.role = FuncionarioRole(role); func.ativo = ativo == "1"
        db.commit()
    return RedirectResponse("/funcionarios", status_code=302)


# ---------------------------------------------------------------------------
# Inadimplentes
# ---------------------------------------------------------------------------

@app.get("/inadimplentes", response_class=HTMLResponse)
def inadimplentes_page(request: Request, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.services.relatorio import relatorio_inadimplentes, stats_inadimplentes
    inadimplentes = relatorio_inadimplentes(db)
    stats = stats_inadimplentes(inadimplentes)
    return templates.TemplateResponse(request, "inadimplentes.html", {
        "inadimplentes": inadimplentes,
        "total_em_aberto": stats["total_em_aberto"],
        "media_dias_atraso": stats["media_dias_atraso"],
        "hoje": date.today().isoformat(),
    })


# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

@app.get("/configuracoes", response_class=HTMLResponse)
def config_page(request: Request, db: Session = Depends(get_tenant_session), current_user=Depends(get_current_funcionario)):
    from app.models.tenant import Notificacao
    from sqlalchemy.orm import joinedload
    notificacoes = (db.query(Notificacao).options(joinedload(Notificacao.aluno))
                    .order_by(Notificacao.criado_em.desc()).limit(20).all())
    return templates.TemplateResponse(request, "configuracoes.html", {"notificacoes": notificacoes})


@app.post("/configuracoes/senha")
async def trocar_senha_form(
    request: Request,
    senha_atual: str = Form(...), nova_senha: str = Form(...), confirmar_senha: str = Form(...),
    db: Session = Depends(get_tenant_session), current_user=Depends(get_current_funcionario),
):
    from app.models.tenant import Notificacao
    from sqlalchemy.orm import joinedload
    from app.services.aluno import trocar_senha_funcionario

    notificacoes = (db.query(Notificacao).options(joinedload(Notificacao.aluno))
                    .order_by(Notificacao.criado_em.desc()).limit(20).all())
    ctx = {"notificacoes": notificacoes}
    if nova_senha != confirmar_senha:
        ctx["error"] = "A nova senha e a confirmação não coincidem."
    else:
        try:
            trocar_senha_funcionario(current_user.id, senha_atual, nova_senha, db)
            ctx["success"] = "Senha alterada com sucesso!"
        except Exception as e:
            ctx["error"] = str(e)
    return templates.TemplateResponse(request, "configuracoes.html", ctx)


@app.post("/configuracoes/notificacoes/disparar")
async def disparar_notificacoes(
    dias_antecedencia: int = Form(5),
    db: Session = Depends(get_tenant_session), _=Depends(require_admin),
):
    from app.services.notificacao import gerar_notificacoes_vencimento, processar_notificacoes_pendentes
    gerar_notificacoes_vencimento(db, dias_antecedencia)
    processar_notificacoes_pendentes(db)
    return RedirectResponse("/configuracoes", status_code=302)


# ---------------------------------------------------------------------------
# Exercícios
# ---------------------------------------------------------------------------

@app.get("/exercicios", response_class=HTMLResponse)
def exercicios_page(request: Request, busca: str = None, grupo: str = None,
                    db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.models.tenant import Exercicio
    q = db.query(Exercicio)
    if busca:
        q = q.filter(Exercicio.nome.ilike(f"%{busca}%"))
    if grupo:
        q = q.filter(Exercicio.grupo_muscular == grupo)
    exercicios = q.order_by(Exercicio.nome).all()
    grupos = sorted({e.grupo_muscular for e in db.query(Exercicio).all() if e.grupo_muscular})
    return templates.TemplateResponse(request, "exercicios.html", {
        "exercicios": exercicios, "grupos": grupos,
        "busca": busca, "grupo_filtro": grupo,
    })


@app.post("/exercicios")
async def criar_exercicio_form(
    request: Request,
    nome: str = Form(...), grupo_muscular: str = Form(None), descricao: str = Form(None),
    db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin),
):
    from app.services.treino import criar_exercicio
    from app.models.tenant import Exercicio
    success = error = None
    try:
        criar_exercicio(nome, grupo_muscular or None, descricao or None, db)
        success = f"Exercício '{nome}' criado!"
    except Exception as e:
        error = str(e)
    exercicios = db.query(Exercicio).order_by(Exercicio.nome).all()
    grupos = sorted({e.grupo_muscular for e in exercicios if e.grupo_muscular})
    return templates.TemplateResponse(request, "exercicios.html", {
        "exercicios": exercicios, "grupos": grupos,
        "success": success, "error": error,
    })


@app.post("/exercicios/editar")
async def editar_exercicio_form(
    ex_id: int = Form(...), nome: str = Form(...),
    grupo_muscular: str = Form(None), descricao: str = Form(None), ativo: str = Form("1"),
    db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin),
):
    from app.models.tenant import Exercicio
    ex = db.query(Exercicio).filter(Exercicio.id == ex_id).first()
    if ex:
        ex.nome = nome
        ex.grupo_muscular = grupo_muscular or None
        ex.descricao = descricao or None
        ex.ativo = ativo == "1"
        db.commit()
    return RedirectResponse("/exercicios", status_code=302)


@app.post("/exercicios/{ex_id}/ativar")
async def ativar_exercicio(ex_id: int, db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.models.tenant import Exercicio
    ex = db.query(Exercicio).filter(Exercicio.id == ex_id).first()
    if ex: ex.ativo = True; db.commit()
    return RedirectResponse("/exercicios", status_code=302)


@app.post("/exercicios/{ex_id}/desativar")
async def desativar_exercicio(ex_id: int, db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    from app.models.tenant import Exercicio
    ex = db.query(Exercicio).filter(Exercicio.id == ex_id).first()
    if ex: ex.ativo = False; db.commit()
    return RedirectResponse("/exercicios", status_code=302)


# ---------------------------------------------------------------------------
# Relatórios Financeiros
# ---------------------------------------------------------------------------

@app.get("/relatorios", response_class=HTMLResponse)
def relatorios_page(request: Request, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    from app.services.relatorio import relatorio_financeiro
    return templates.TemplateResponse(request, "relatorios.html", {
        "dados": relatorio_financeiro(db)
    })


@app.get("/relatorios/exportar-csv")
def exportar_relatorio_csv(db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    import csv, io
    from app.models.tenant import Pagamento, PagamentoStatus, Aluno, Matricula, Plano
    from sqlalchemy.orm import joinedload
    from fastapi.responses import StreamingResponse

    rows = (
        db.query(Pagamento)
        .options(
            joinedload(Pagamento.matricula).joinedload(Matricula.aluno),
            joinedload(Pagamento.matricula).joinedload(Matricula.plano),
        )
        .order_by(Pagamento.data_vencimento.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Aluno", "Plano", "Valor (R$)", "Vencimento", "Pagamento", "Status", "Método"])
    for p in rows:
        aluno = p.matricula.aluno.nome if p.matricula and p.matricula.aluno else ""
        plano = p.matricula.plano.nome if p.matricula and p.matricula.plano else ""
        writer.writerow([
            p.id, aluno, plano,
            f"{p.valor:.2f}",
            p.data_vencimento.strftime("%d/%m/%Y") if p.data_vencimento else "",
            p.data_pagamento.strftime("%d/%m/%Y") if p.data_pagamento else "",
            p.status.value,
            p.metodo.value if p.metodo else "",
        ])

    output.seek(0)
    filename = f"relatorio_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Superadmin
# ---------------------------------------------------------------------------

@app.get("/superadmin", response_class=HTMLResponse)
def superadmin_page(request: Request, db: Session = Depends(get_db), _=Depends(require_superadmin)):
    from app.services.academia import listar_academias
    return templates.TemplateResponse(request, "superadmin.html", {"academias": listar_academias(db)})


@app.post("/superadmin/academias/form")
async def criar_academia_form(
    request: Request,
    nome: str = Form(...), slug: str = Form(...),
    cnpj: str = Form(None), telefone: str = Form(None), email: str = Form(None),
    endereco: str = Form(None),
    admin_nome: str = Form(None), admin_email: str = Form(None), admin_senha: str = Form(None),
    db: Session = Depends(get_db), _=Depends(require_superadmin),
):
    from app.schemas.public import AcademiaCreate
    from app.services.academia import criar_academia, listar_academias
    try:
        academia = criar_academia(AcademiaCreate(nome=nome, slug=slug, cnpj=cnpj or None,
                                      telefone=telefone or None, email=email or None,
                                      endereco=endereco or None), db)
        # Criar funcionário admin na academia, se dados fornecidos
        if admin_nome and admin_email and admin_senha:
            tenant_db = next(get_tenant_db(academia.schema_name))
            try:
                from app.models.tenant import Funcionario, FuncionarioRole
                tenant_db.add(Funcionario(
                    nome=admin_nome, email=admin_email,
                    senha_hash=hash_password(admin_senha),
                    role=FuncionarioRole.admin, ativo=True,
                ))
                tenant_db.commit()
            finally:
                tenant_db.close()
        return templates.TemplateResponse(request, "superadmin.html", {"academias": listar_academias(db), "success": f"Academia '{nome}' criada!"})
    except Exception as e:
        return templates.TemplateResponse(request, "superadmin.html", {"academias": listar_academias(db), "error": str(e)})


@app.post("/superadmin/academias/{academia_id}/editar")
async def editar_academia_form(
    request: Request,
    academia_id: int,
    nome: str = Form(...),
    cnpj: str = Form(None),
    telefone: str = Form(None),
    email: str = Form(None),
    endereco: str = Form(None),
    db: Session = Depends(get_db), _=Depends(require_superadmin),
):
    from app.schemas.public import AcademiaUpdate
    from app.services.academia import atualizar_academia, listar_academias
    try:
        atualizar_academia(academia_id, AcademiaUpdate(
            nome=nome, cnpj=cnpj or None, telefone=telefone or None,
            email=email or None, endereco=endereco or None,
        ), db)
        return templates.TemplateResponse(request, "superadmin.html", {"academias": listar_academias(db), "success": "Academia atualizada!"})
    except Exception as e:
        return templates.TemplateResponse(request, "superadmin.html", {"academias": listar_academias(db), "error": str(e)})


@app.post("/superadmin/academias/{academia_id}/ativar")
async def ativar_academia_form(
    request: Request, academia_id: int,
    db: Session = Depends(get_db), _=Depends(require_superadmin),
):
    from app.schemas.public import AcademiaUpdate, AcademiaStatus
    from app.services.academia import atualizar_academia, listar_academias
    atualizar_academia(academia_id, AcademiaUpdate(status=AcademiaStatus.ativa), db)
    return templates.TemplateResponse(request, "superadmin.html", {"academias": listar_academias(db), "success": "Academia ativada!"})


@app.post("/superadmin/academias/{academia_id}/desativar")
async def desativar_academia_form(
    request: Request, academia_id: int,
    db: Session = Depends(get_db), _=Depends(require_superadmin),
):
    from app.schemas.public import AcademiaUpdate, AcademiaStatus
    from app.services.academia import atualizar_academia, listar_academias
    atualizar_academia(academia_id, AcademiaUpdate(status=AcademiaStatus.inativa), db)
    return templates.TemplateResponse(request, "superadmin.html", {"academias": listar_academias(db), "success": "Academia desativada!"})
