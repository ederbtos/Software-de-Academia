from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.schemas.tenant import AlunoCreate, MatriculaCreate, PagamentoRegistrar
from app.services import aluno as aluno_service
from app.models.tenant import PagamentoMetodo, PagamentoStatus


def test_criar_aluno_valido(db_session):
    aluno = aluno_service.criar_aluno(AlunoCreate(nome="Novo Aluno", email="novo@fit.com"), db_session)
    assert aluno.id is not None
    assert aluno.nome == "Novo Aluno"


def test_criar_aluno_email_duplicado(db_session, seed_tenant):
    with pytest.raises(HTTPException):
        aluno_service.criar_aluno(AlunoCreate(nome="Outro", email=seed_tenant["aluno"].email), db_session)


def test_matricular_aluno_gera_pagamento(db_session, seed_tenant):
    aluno_id = seed_tenant["aluno"].id
    plano_id = seed_tenant["plano"].id
    data_inicio = seed_tenant["hoje"]
    mat = aluno_service.matricular_aluno(
        MatriculaCreate(aluno_id=aluno_id, plano_id=plano_id, data_inicio=data_inicio),
        db_session,
    )
    assert mat.id is not None
    assert mat.data_vencimento == data_inicio + timedelta(days=seed_tenant["plano"].duracao_dias)
    assert len(mat.pagamentos) == 1
    assert mat.pagamentos[0].status == PagamentoStatus.pendente


def test_registrar_pagamento(db_session, seed_tenant):
    mat = aluno_service.matricular_aluno(
        MatriculaCreate(
            aluno_id=seed_tenant["aluno"].id,
            plano_id=seed_tenant["plano"].id,
            data_inicio=seed_tenant["hoje"],
        ),
        db_session,
    )
    pag = mat.pagamentos[0]
    out = aluno_service.registrar_pagamento(
        pag.id, PagamentoRegistrar(metodo=PagamentoMetodo.pix), db_session
    )
    assert out.status == PagamentoStatus.pago
