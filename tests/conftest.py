import sys
from pathlib import Path
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import Base
from app.models.tenant import Aluno, Funcionario, FuncionarioRole, Plano


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    tenant_tables = [t for name, t in Base.metadata.tables.items() if "." not in name]
    Base.metadata.create_all(bind=engine, tables=tenant_tables)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def seed_tenant(db_session):
    admin = Funcionario(
        nome="Admin",
        email="admin@fit.com",
        senha_hash="hash",
        role=FuncionarioRole.admin,
        ativo=True,
    )
    aluno = Aluno(nome="Aluno Teste", email="aluno@fit.com", ativo=True)
    plano = Plano(nome="Mensal", valor=120, duracao_dias=30, ativo=True)
    db_session.add_all([admin, aluno, plano])
    db_session.commit()
    return {"admin": admin, "aluno": aluno, "plano": plano, "hoje": date.today()}
