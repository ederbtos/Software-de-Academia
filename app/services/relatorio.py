from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from app.models.tenant import (
    Aluno, Presenca, Pagamento, PagamentoStatus,
    Treino, AvaliacaoFisica, Matricula
)
from app.schemas.tenant import DashboardOut


def get_dashboard(db: Session) -> DashboardOut:
    hoje = date.today()
    mes_inicio = hoje.replace(day=1)

    total_ativos = db.query(func.count(Aluno.id)).filter(Aluno.ativo == True).scalar() or 0
    total_inativos = db.query(func.count(Aluno.id)).filter(Aluno.ativo == False).scalar() or 0

    checkins_hoje = (
        db.query(func.count(Presenca.id))
        .filter(func.date(Presenca.data_hora) == hoje)
        .scalar() or 0
    )

    em_atraso = (
        db.query(func.count(Pagamento.id))
        .filter(
            Pagamento.status == PagamentoStatus.pendente,
            Pagamento.data_vencimento < hoje,
        )
        .scalar() or 0
    )

    receita_mes = (
        db.query(func.coalesce(func.sum(Pagamento.valor), 0))
        .filter(
            Pagamento.status == PagamentoStatus.pago,
            Pagamento.data_pagamento >= mes_inicio,
            Pagamento.data_pagamento <= hoje,
        )
        .scalar() or Decimal("0.00")
    )

    alunos_com_treino = (
        db.query(Treino.aluno_id)
        .filter(Treino.ativo == True)
        .distinct()
        .subquery()
    )
    sem_treino = (
        db.query(func.count(Aluno.id))
        .filter(Aluno.ativo == True, ~Aluno.id.in_(alunos_com_treino))
        .scalar() or 0
    )

    avaliacoes_mes = (
        db.query(func.count(AvaliacaoFisica.id))
        .filter(AvaliacaoFisica.data >= mes_inicio)
        .scalar() or 0
    )

    return DashboardOut(
        total_alunos_ativos=total_ativos,
        total_alunos_inativos=total_inativos,
        checkins_hoje=checkins_hoje,
        mensalidades_em_atraso=em_atraso,
        receita_mes_atual=receita_mes,
        alunos_sem_treino=sem_treino,
        avaliacoes_mes_atual=avaliacoes_mes,
    )


def relatorio_inadimplentes(db: Session):
    hoje = date.today()
    return (
        db.query(Aluno, Pagamento)
        .join(Matricula, Matricula.aluno_id == Aluno.id)
        .join(Pagamento, Pagamento.matricula_id == Matricula.id)
        .filter(
            Pagamento.status == PagamentoStatus.pendente,
            Pagamento.data_vencimento < hoje,
            Aluno.ativo == True,
        )
        .all()
    )
