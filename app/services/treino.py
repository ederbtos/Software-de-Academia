from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.tenant import (
    Treino, TreinoExercicio, Exercicio, AvaliacaoFisica, Presenca
)
from app.schemas.tenant import TreinoCreate, AvaliacaoCreate, PresencaCreate


# ---------------------------------------------------------------------------
# Presença
# ---------------------------------------------------------------------------

def registrar_presenca(data: PresencaCreate, db: Session) -> Presenca:
    from app.models.tenant import Aluno
    aluno = db.query(Aluno).filter(Aluno.id == data.aluno_id, Aluno.ativo == True).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    presenca = Presenca(aluno_id=data.aluno_id, observacoes=data.observacoes)
    db.add(presenca)
    db.commit()
    db.refresh(presenca)
    return presenca


def listar_presencas_aluno(aluno_id: int, db: Session):
    return db.query(Presenca).filter(Presenca.aluno_id == aluno_id).order_by(Presenca.data_hora.desc()).all()


# ---------------------------------------------------------------------------
# Avaliação Física
# ---------------------------------------------------------------------------

def _calcular_imc(peso_kg, altura_cm) -> Decimal | None:
    if peso_kg and altura_cm and altura_cm > 0:
        altura_m = float(altura_cm) / 100
        return round(Decimal(str(float(peso_kg) / (altura_m ** 2))), 2)
    return None


def criar_avaliacao(data: AvaliacaoCreate, db: Session) -> AvaliacaoFisica:
    imc = _calcular_imc(data.peso_kg, data.altura_cm)
    avaliacao = AvaliacaoFisica(**data.model_dump(), imc=imc)
    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)
    return avaliacao


def listar_avaliacoes_aluno(aluno_id: int, db: Session):
    return (
        db.query(AvaliacaoFisica)
        .filter(AvaliacaoFisica.aluno_id == aluno_id)
        .order_by(AvaliacaoFisica.data.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Exercícios
# ---------------------------------------------------------------------------

def listar_exercicios(db: Session):
    return db.query(Exercicio).filter(Exercicio.ativo == True).order_by(Exercicio.nome).all()


def criar_exercicio(nome: str, grupo_muscular: str | None, descricao: str | None, db: Session) -> Exercicio:
    ex = Exercicio(nome=nome, grupo_muscular=grupo_muscular, descricao=descricao)
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


# ---------------------------------------------------------------------------
# Treinos
# ---------------------------------------------------------------------------

def criar_treino(data: TreinoCreate, db: Session) -> Treino:
    treino_data = data.model_dump(exclude={"exercicios"})
    treino = Treino(**treino_data)
    db.add(treino)
    db.flush()

    for i, ex_data in enumerate(data.exercicios, start=1):
        exercicio = db.query(Exercicio).filter(Exercicio.id == ex_data.exercicio_id).first()
        if not exercicio:
            raise HTTPException(status_code=404, detail=f"Exercício {ex_data.exercicio_id} não encontrado")
        item = TreinoExercicio(
            treino_id=treino.id,
            **ex_data.model_dump(),
            ordem=ex_data.ordem or i,
        )
        db.add(item)

    db.commit()
    db.refresh(treino)
    return treino


def listar_treinos_aluno(aluno_id: int, db: Session):
    return (
        db.query(Treino)
        .filter(Treino.aluno_id == aluno_id, Treino.ativo == True)
        .order_by(Treino.identificador)
        .all()
    )


def buscar_treino(treino_id: int, db: Session) -> Treino:
    treino = db.query(Treino).filter(Treino.id == treino_id).first()
    if not treino:
        raise HTTPException(status_code=404, detail="Treino não encontrado")
    return treino
