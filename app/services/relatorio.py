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
    from app.models.tenant import Plano
    from datetime import timedelta
    hoje = date.today()
    rows = (
        db.query(Aluno, Pagamento, Matricula, Plano)
        .join(Matricula, Matricula.aluno_id == Aluno.id)
        .join(Pagamento, Pagamento.matricula_id == Matricula.id)
        .join(Plano, Plano.id == Matricula.plano_id)
        .filter(
            Pagamento.status == PagamentoStatus.pendente,
            Pagamento.data_vencimento < hoje,
            Aluno.ativo == True,
        )
        .all()
    )
    result = []
    for aluno, pag, mat, plano in rows:
        dias = (hoje - pag.data_vencimento).days
        result.append({
            "aluno_id": aluno.id,
            "aluno_nome": aluno.nome,
            "telefone": aluno.telefone,
            "plano_nome": plano.nome,
            "vencimento": pag.data_vencimento,
            "dias_atraso": dias,
            "valor": pag.valor,
            "pagamento_id": pag.id,
        })
    return result


def stats_inadimplentes(inadimplentes: list) -> dict:
    total = sum(float(r["valor"]) for r in inadimplentes)
    media = (sum(r["dias_atraso"] for r in inadimplentes) / len(inadimplentes)) if inadimplentes else 0
    return {"total_em_aberto": total, "media_dias_atraso": media}


def relatorio_financeiro(db: Session) -> dict:
    """Retorna receita mensal dos últimos 12 meses e totais por método de pagamento."""
    from sqlalchemy import extract
    from app.models.tenant import PagamentoMetodo
    from datetime import datetime

    hoje = date.today()

    # Receita por mês (últimos 12 meses)
    receita_mensal = []
    for i in range(11, -1, -1):
        if hoje.month - i <= 0:
            mes = hoje.month - i + 12
            ano = hoje.year - 1
        else:
            mes = hoje.month - i
            ano = hoje.year

        total = (
            db.query(func.coalesce(func.sum(Pagamento.valor), 0))
            .filter(
                Pagamento.status == PagamentoStatus.pago,
                extract("month", Pagamento.data_pagamento) == mes,
                extract("year", Pagamento.data_pagamento) == ano,
            )
            .scalar()
        )
        receita_mensal.append({
            "mes": f"{mes:02d}/{ano}",
            "total": float(total or 0),
        })

    # Totais por método de pagamento (mês atual)
    mes_inicio = hoje.replace(day=1)
    por_metodo = []
    for metodo in PagamentoMetodo:
        total_m = (
            db.query(func.coalesce(func.sum(Pagamento.valor), 0))
            .filter(
                Pagamento.status == PagamentoStatus.pago,
                Pagamento.metodo == metodo,
                Pagamento.data_pagamento >= mes_inicio,
            )
            .scalar()
        )
        if float(total_m or 0) > 0:
            por_metodo.append({"metodo": metodo.value, "total": float(total_m)})

    # Totais gerais
    total_mes = sum(r["total"] for r in receita_mensal[-1:])
    total_ano = sum(r["total"] for r in receita_mensal)
    total_pendente = float(
        db.query(func.coalesce(func.sum(Pagamento.valor), 0))
        .filter(Pagamento.status == PagamentoStatus.pendente)
        .scalar() or 0
    )

    return {
        "receita_mensal": receita_mensal,
        "por_metodo": por_metodo,
        "total_mes_atual": total_mes,
        "total_ano": total_ano,
        "total_pendente": total_pendente,
    }

