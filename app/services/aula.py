from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.tenant import Aula, InscricaoAula, InscricaoStatus
from app.schemas.tenant import AulaCreate, InscricaoCreate


def listar_aulas(db: Session):
    return db.query(Aula).filter(Aula.ativa == True).order_by(Aula.dia_semana, Aula.horario_inicio).all()


def criar_aula(data: AulaCreate, db: Session) -> Aula:
    from datetime import time
    h_ini = time.fromisoformat(data.horario_inicio)
    h_fim = time.fromisoformat(data.horario_fim)
    aula = Aula(
        nome=data.nome,
        professor_id=data.professor_id,
        dia_semana=data.dia_semana,
        horario_inicio=h_ini,
        horario_fim=h_fim,
        capacidade_maxima=data.capacidade_maxima,
    )
    db.add(aula)
    db.commit()
    db.refresh(aula)
    return aula


def inscrever_aluno(data: InscricaoCreate, db: Session) -> InscricaoAula:
    aula = db.query(Aula).filter(Aula.id == data.aula_id, Aula.ativa == True).first()
    if not aula:
        raise HTTPException(status_code=404, detail="Aula não encontrada")

    # Verifica se já está inscrito
    existente = (
        db.query(InscricaoAula)
        .filter(
            InscricaoAula.aluno_id == data.aluno_id,
            InscricaoAula.aula_id == data.aula_id,
            InscricaoAula.status != InscricaoStatus.cancelada,
        )
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail="Aluno já inscrito nesta aula")

    confirmadas = (
        db.query(InscricaoAula)
        .filter(InscricaoAula.aula_id == data.aula_id, InscricaoAula.status == InscricaoStatus.confirmada)
        .count()
    )

    s = InscricaoStatus.confirmada if confirmadas < aula.capacidade_maxima else InscricaoStatus.lista_espera
    inscricao = InscricaoAula(aluno_id=data.aluno_id, aula_id=data.aula_id, status=s)
    db.add(inscricao)
    db.commit()
    db.refresh(inscricao)
    return inscricao


def cancelar_inscricao(inscricao_id: int, db: Session) -> InscricaoAula:
    inscricao = db.query(InscricaoAula).filter(InscricaoAula.id == inscricao_id).first()
    if not inscricao:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada")
    inscricao.status = InscricaoStatus.cancelada
    db.commit()

    # Promove o primeiro da lista de espera
    proximo = (
        db.query(InscricaoAula)
        .filter(
            InscricaoAula.aula_id == inscricao.aula_id,
            InscricaoAula.status == InscricaoStatus.lista_espera,
        )
        .order_by(InscricaoAula.data_inscricao)
        .first()
    )
    if proximo:
        proximo.status = InscricaoStatus.confirmada
        db.commit()

    db.refresh(inscricao)
    return inscricao
