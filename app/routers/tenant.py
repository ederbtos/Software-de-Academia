from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.deps import get_tenant_session, require_professor_or_admin, require_admin, get_current_funcionario
from app.schemas.tenant import (
    AlunoCreate, AlunoUpdate, AlunoOut,
    MatriculaCreate, MatriculaOut,
    PagamentoCreate, PagamentoRegistrar, PagamentoOut,
    PresencaCreate, PresencaOut,
    AvaliacaoCreate, AvaliacaoOut,
    TreinoCreate, TreinoOut,
    ExercicioCreate, ExercicioOut,
    AulaCreate, AulaOut,
    InscricaoCreate, InscricaoOut,
    PlanoCreate, PlanoUpdate, PlanoOut,
    FuncionarioCreate, FuncionarioUpdate, FuncionarioOut,
    DashboardOut,
)
from app.services import aluno as svc_aluno
from app.services import treino as svc_treino
from app.services import aula as svc_aula
from app.services import relatorio as svc_relatorio
from app.models.tenant import Funcionario, Plano, Pagamento
from app.core.security import hash_password

router = APIRouter()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_relatorio.get_dashboard(db)


# ---------------------------------------------------------------------------
# Alunos
# ---------------------------------------------------------------------------

@router.get("/alunos", response_model=list[AlunoOut])
def listar_alunos(apenas_ativos: bool = True, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aluno.listar_alunos(db, apenas_ativos)


@router.get("/alunos/{aluno_id}", response_model=AlunoOut)
def get_aluno(aluno_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aluno.buscar_aluno(aluno_id, db)


@router.post("/alunos", response_model=AlunoOut, status_code=201)
def criar_aluno(data: AlunoCreate, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aluno.criar_aluno(data, db)


@router.patch("/alunos/{aluno_id}", response_model=AlunoOut)
def atualizar_aluno(aluno_id: int, data: AlunoUpdate, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aluno.atualizar_aluno(aluno_id, data, db)


# ---------------------------------------------------------------------------
# Matrículas
# ---------------------------------------------------------------------------

@router.post("/matriculas", response_model=MatriculaOut, status_code=201)
def criar_matricula(data: MatriculaCreate, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aluno.matricular_aluno(data, db)


# ---------------------------------------------------------------------------
# Pagamentos
# ---------------------------------------------------------------------------

@router.get("/pagamentos/inadimplentes")
def inadimplentes(db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_relatorio.relatorio_inadimplentes(db)


@router.patch("/pagamentos/{pagamento_id}/pagar", response_model=PagamentoOut)
def registrar_pagamento(pagamento_id: int, data: PagamentoRegistrar, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aluno.registrar_pagamento(pagamento_id, data, db)


# ---------------------------------------------------------------------------
# Presença
# ---------------------------------------------------------------------------

@router.post("/presencas", response_model=PresencaOut, status_code=201)
def checkin(data: PresencaCreate, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_treino.registrar_presenca(data, db)


@router.get("/presencas/aluno/{aluno_id}", response_model=list[PresencaOut])
def presencas_aluno(aluno_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_treino.listar_presencas_aluno(aluno_id, db)


# ---------------------------------------------------------------------------
# Avaliação Física
# ---------------------------------------------------------------------------

@router.post("/avaliacoes", response_model=AvaliacaoOut, status_code=201)
def criar_avaliacao(data: AvaliacaoCreate, db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    return svc_treino.criar_avaliacao(data, db)


@router.get("/avaliacoes/aluno/{aluno_id}", response_model=list[AvaliacaoOut])
def avaliacoes_aluno(aluno_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_treino.listar_avaliacoes_aluno(aluno_id, db)


# ---------------------------------------------------------------------------
# Exercícios
# ---------------------------------------------------------------------------

@router.get("/exercicios", response_model=list[ExercicioOut])
def listar_exercicios(db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_treino.listar_exercicios(db)


@router.post("/exercicios", response_model=ExercicioOut, status_code=201)
def criar_exercicio(data: ExercicioCreate, db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    return svc_treino.criar_exercicio(data.nome, data.grupo_muscular, data.descricao, db)


# ---------------------------------------------------------------------------
# Treinos
# ---------------------------------------------------------------------------

@router.post("/treinos", response_model=TreinoOut, status_code=201)
def criar_treino(data: TreinoCreate, db: Session = Depends(get_tenant_session), _=Depends(require_professor_or_admin)):
    return svc_treino.criar_treino(data, db)


@router.get("/treinos/aluno/{aluno_id}", response_model=list[TreinoOut])
def treinos_aluno(aluno_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_treino.listar_treinos_aluno(aluno_id, db)


@router.get("/treinos/{treino_id}", response_model=TreinoOut)
def get_treino(treino_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_treino.buscar_treino(treino_id, db)


# ---------------------------------------------------------------------------
# Aulas Coletivas
# ---------------------------------------------------------------------------

@router.get("/aulas", response_model=list[AulaOut])
def listar_aulas(db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aula.listar_aulas(db)


@router.post("/aulas", response_model=AulaOut, status_code=201)
def criar_aula(data: AulaCreate, db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    return svc_aula.criar_aula(data, db)


@router.post("/aulas/inscricao", response_model=InscricaoOut, status_code=201)
def inscrever(data: InscricaoCreate, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aula.inscrever_aluno(data, db)


@router.delete("/aulas/inscricao/{inscricao_id}", response_model=InscricaoOut)
def cancelar_inscricao(inscricao_id: int, db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return svc_aula.cancelar_inscricao(inscricao_id, db)


# ---------------------------------------------------------------------------
# Planos
# ---------------------------------------------------------------------------

@router.get("/planos", response_model=list[PlanoOut])
def listar_planos(db: Session = Depends(get_tenant_session), _=Depends(get_current_funcionario)):
    return db.query(Plano).filter(Plano.ativo == True).all()


@router.post("/planos", response_model=PlanoOut, status_code=201)
def criar_plano(data: PlanoCreate, db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    plano = Plano(**data.model_dump())
    db.add(plano)
    db.commit()
    db.refresh(plano)
    return plano


@router.patch("/planos/{plano_id}", response_model=PlanoOut)
def atualizar_plano(plano_id: int, data: PlanoUpdate, db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not plano:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(plano, k, v)
    db.commit()
    db.refresh(plano)
    return plano


# ---------------------------------------------------------------------------
# Funcionários
# ---------------------------------------------------------------------------

@router.get("/funcionarios", response_model=list[FuncionarioOut])
def listar_funcionarios(db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    return db.query(Funcionario).order_by(Funcionario.nome).all()


@router.post("/funcionarios", response_model=FuncionarioOut, status_code=201)
def criar_funcionario(data: FuncionarioCreate, db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    if db.query(Funcionario).filter(Funcionario.email == data.email).first():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    func_data = data.model_dump(exclude={"password"})
    func = Funcionario(**func_data, senha_hash=hash_password(data.password))
    db.add(func)
    db.commit()
    db.refresh(func)
    return func


@router.patch("/funcionarios/{func_id}", response_model=FuncionarioOut)
def atualizar_funcionario(func_id: int, data: FuncionarioUpdate, db: Session = Depends(get_tenant_session), _=Depends(require_admin)):
    func = db.query(Funcionario).filter(Funcionario.id == func_id).first()
    if not func:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(func, k, v)
    db.commit()
    db.refresh(func)
    return func
