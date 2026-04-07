from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.tenant import Aluno, Matricula, Pagamento, MatriculaStatus, PagamentoStatus
from app.schemas.tenant import AlunoCreate, AlunoUpdate, MatriculaCreate, PagamentoRegistrar


def listar_alunos(db: Session, apenas_ativos: bool = True):
    q = db.query(Aluno)
    if apenas_ativos:
        q = q.filter(Aluno.ativo == True)
    return q.order_by(Aluno.nome).all()


def buscar_aluno(aluno_id: int, db: Session) -> Aluno:
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return aluno


def criar_aluno(data: AlunoCreate, db: Session) -> Aluno:
    if data.cpf and db.query(Aluno).filter(Aluno.cpf == data.cpf).first():
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    if data.email and db.query(Aluno).filter(Aluno.email == data.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    aluno = Aluno(**data.model_dump())
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    return aluno


def atualizar_aluno(aluno_id: int, data: AlunoUpdate, db: Session) -> Aluno:
    aluno = buscar_aluno(aluno_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(aluno, field, value)
    db.commit()
    db.refresh(aluno)
    return aluno


def matricular_aluno(data: MatriculaCreate, db: Session) -> Matricula:
    from app.models.tenant import Plano
    aluno = buscar_aluno(data.aluno_id, db)
    plano = db.query(Plano).filter(Plano.id == data.plano_id, Plano.ativo == True).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    from datetime import timedelta
    data_vencimento = data.data_inicio + timedelta(days=plano.duracao_dias)

    matricula = Matricula(
        aluno_id=data.aluno_id,
        plano_id=data.plano_id,
        data_inicio=data.data_inicio,
        data_vencimento=data_vencimento,
        status=MatriculaStatus.ativa,
        observacoes=data.observacoes,
    )
    db.add(matricula)
    db.flush()

    # Gera o primeiro pagamento automaticamente
    pagamento = Pagamento(
        matricula_id=matricula.id,
        valor=plano.valor,
        data_vencimento=data_vencimento,
        status=PagamentoStatus.pendente,
    )
    db.add(pagamento)
    db.commit()
    db.refresh(matricula)
    return matricula


def registrar_pagamento(pagamento_id: int, data: PagamentoRegistrar, db: Session) -> Pagamento:
    pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    pagamento.status = PagamentoStatus.pago
    pagamento.metodo = data.metodo
    pagamento.data_pagamento = data.data_pagamento or date.today()
    if data.observacoes:
        pagamento.observacoes = data.observacoes
    db.commit()
    db.refresh(pagamento)
    return pagamento


def atualizar_status_matriculas(db: Session):
    """Atualiza matrículas vencidas (deve ser chamado periodicamente)."""
    hoje = date.today()
    db.query(Matricula).filter(
        Matricula.data_vencimento < hoje,
        Matricula.status == MatriculaStatus.ativa,
    ).update({"status": MatriculaStatus.vencida})
    db.commit()
