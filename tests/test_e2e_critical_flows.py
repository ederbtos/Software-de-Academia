from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_current_funcionario, get_tenant_session
from app.core.csrf import CSRF_COOKIE_NAME
from app.db.database import Base
from app.models.tenant import Aluno, Funcionario, FuncionarioRole, Matricula, Pagamento, Plano, Presenca
from main import app


def _make_current_user():
    return SimpleNamespace(id=1, role=SimpleNamespace(value="admin"))


def _make_user_with_role(role: str):
    return SimpleNamespace(id=1, role=SimpleNamespace(value=role))


def _csrf_from_client(client: TestClient) -> str:
    token = client.cookies.get(CSRF_COOKIE_NAME)
    assert token
    return token


@pytest.fixture()
def e2e_db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tenant_tables = [t for name, t in Base.metadata.tables.items() if "." not in name]
    Base.metadata.create_all(bind=engine, tables=tenant_tables)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        db.add(Funcionario(
            nome="Admin",
            email="admin@fit.com",
            senha_hash="hash",
            role=FuncionarioRole.admin,
            ativo=True,
        ))
        db.add(Aluno(nome="Aluno Base", email="aluno.base@fit.com", ativo=True))
        db.add(Plano(nome="Mensal", valor=120, duracao_dias=30, ativo=True))
        db.commit()
        yield db
    finally:
        db.close()


def test_fluxo_critico_aluno_matricula_pagamento_e_checkin(e2e_db_session):
    def _override_tenant_session():
        yield e2e_db_session

    def _override_current_funcionario():
        return _make_current_user()

    app.dependency_overrides[get_tenant_session] = _override_tenant_session
    app.dependency_overrides[get_current_funcionario] = _override_current_funcionario

    try:
        client = TestClient(app)

        # Primeira navegação para materializar cookie CSRF.
        resp_alunos = client.get("/alunos")
        assert resp_alunos.status_code == 200
        csrf = _csrf_from_client(client)

        # 1) Cadastro de aluno (fluxo core de CRM).
        resp_criar_aluno = client.post(
            "/alunos",
            headers={"x-csrf-token": csrf},
            data={
                "nome": "Novo Aluno E2E",
                "email": "novo.aluno@fit.com",
                "cpf": "12345678910",
            },
        )
        assert resp_criar_aluno.status_code == 200

        novo_aluno = e2e_db_session.query(Aluno).filter(Aluno.email == "novo.aluno@fit.com").first()
        assert novo_aluno is not None

        # 2) Matrícula + geração de pagamento (fluxo financeiro crítico).
        plano = e2e_db_session.query(Plano).first()
        assert plano is not None

        resp_matricula = client.post(
            "/matriculas",
            headers={"x-csrf-token": csrf},
            data={
                "aluno_id": str(novo_aluno.id),
                "plano_id": str(plano.id),
                "data_inicio": date.today().isoformat(),
                "redirect_url": "/matriculas",
            },
            follow_redirects=False,
        )
        assert resp_matricula.status_code == 302

        matricula = e2e_db_session.query(Matricula).filter(Matricula.aluno_id == novo_aluno.id).first()
        assert matricula is not None
        pagamento = e2e_db_session.query(Pagamento).filter(Pagamento.matricula_id == matricula.id).first()
        assert pagamento is not None

        # 3) Check-in registrado para aluno ativo.
        resp_checkin = client.post(
            "/checkin",
            headers={"x-csrf-token": csrf},
            data={
                "acao": "registrar",
                "aluno_id": str(novo_aluno.id),
                "observacoes": "Teste E2E",
            },
        )
        assert resp_checkin.status_code == 200

        presenca = e2e_db_session.query(Presenca).filter(Presenca.aluno_id == novo_aluno.id).first()
        assert presenca is not None
    finally:
        app.dependency_overrides.clear()


def test_permissao_admin_pode_criar_plano(e2e_db_session):
    def _override_tenant_session():
        yield e2e_db_session

    def _override_current_funcionario():
        return _make_user_with_role("admin")

    app.dependency_overrides[get_tenant_session] = _override_tenant_session
    app.dependency_overrides[get_current_funcionario] = _override_current_funcionario

    try:
        client = TestClient(app)
        assert client.get("/planos").status_code == 200
        csrf = _csrf_from_client(client)

        resp = client.post(
            "/planos",
            headers={"x-csrf-token": csrf},
            data={"nome": "Plano Trimestral", "valor": "199.90", "duracao_dias": "90"},
        )
        assert resp.status_code == 200
        criado = e2e_db_session.query(Plano).filter(Plano.nome == "Plano Trimestral").first()
        assert criado is not None
    finally:
        app.dependency_overrides.clear()


def test_permissao_recepcionista_bloqueado_em_rota_admin(e2e_db_session):
    def _override_tenant_session():
        yield e2e_db_session

    def _override_current_funcionario():
        return _make_user_with_role("recepcionista")

    app.dependency_overrides[get_tenant_session] = _override_tenant_session
    app.dependency_overrides[get_current_funcionario] = _override_current_funcionario

    try:
        client = TestClient(app)
        assert client.get("/planos").status_code == 200
        csrf = _csrf_from_client(client)

        resp = client.post(
            "/planos",
            headers={"x-csrf-token": csrf},
            data={"nome": "Plano Indevido", "valor": "99.90", "duracao_dias": "30"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_permissao_recepcionista_bloqueado_em_rota_professor_ou_admin(e2e_db_session):
    def _override_tenant_session():
        yield e2e_db_session

    def _override_current_funcionario():
        return _make_user_with_role("recepcionista")

    app.dependency_overrides[get_tenant_session] = _override_tenant_session
    app.dependency_overrides[get_current_funcionario] = _override_current_funcionario

    try:
        client = TestClient(app)
        resp = client.get("/treinos/novo")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
