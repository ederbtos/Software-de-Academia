from datetime import datetime, date, time as time_type
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from app.models.tenant import (
    FuncionarioRole, SexoEnum, MatriculaStatus,
    PagamentoStatus, PagamentoMetodo, DiaSemana,
    InscricaoStatus, NotificacaoTipo
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class FuncionarioLoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Funcionários
# ---------------------------------------------------------------------------

class FuncionarioCreate(BaseModel):
    nome: str
    email: EmailStr
    password: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    role: FuncionarioRole = FuncionarioRole.recepcionista


class FuncionarioUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    role: Optional[FuncionarioRole] = None
    ativo: Optional[bool] = None


class FuncionarioOut(BaseModel):
    id: int
    nome: str
    email: str
    cpf: Optional[str]
    telefone: Optional[str]
    role: FuncionarioRole
    ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Planos
# ---------------------------------------------------------------------------

class PlanoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    valor: Decimal
    duracao_dias: int = 30


class PlanoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    valor: Optional[Decimal] = None
    duracao_dias: Optional[int] = None
    ativo: Optional[bool] = None


class PlanoOut(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    valor: Decimal
    duracao_dias: int
    ativo: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Alunos
# ---------------------------------------------------------------------------

class AlunoCreate(BaseModel):
    nome: str
    email: Optional[EmailStr] = None
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    data_nascimento: Optional[date] = None
    sexo: Optional[SexoEnum] = None
    endereco: Optional[str] = None
    observacoes: Optional[str] = None


class AlunoUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    data_nascimento: Optional[date] = None
    sexo: Optional[SexoEnum] = None
    endereco: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class AlunoOut(BaseModel):
    id: int
    nome: str
    email: Optional[str]
    cpf: Optional[str]
    telefone: Optional[str]
    data_nascimento: Optional[date]
    sexo: Optional[SexoEnum]
    endereco: Optional[str]
    ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Matrículas
# ---------------------------------------------------------------------------

class MatriculaCreate(BaseModel):
    aluno_id: int
    plano_id: int
    data_inicio: date
    observacoes: Optional[str] = None


class MatriculaOut(BaseModel):
    id: int
    aluno_id: int
    plano_id: int
    data_inicio: date
    data_vencimento: date
    status: MatriculaStatus
    observacoes: Optional[str]
    plano: PlanoOut

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pagamentos
# ---------------------------------------------------------------------------

class PagamentoCreate(BaseModel):
    matricula_id: int
    valor: Decimal
    data_vencimento: date
    observacoes: Optional[str] = None


class PagamentoRegistrar(BaseModel):
    metodo: PagamentoMetodo
    data_pagamento: Optional[date] = None
    observacoes: Optional[str] = None


class PagamentoOut(BaseModel):
    id: int
    matricula_id: int
    valor: Decimal
    data_vencimento: date
    data_pagamento: Optional[date]
    status: PagamentoStatus
    metodo: Optional[PagamentoMetodo]
    observacoes: Optional[str]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Presença
# ---------------------------------------------------------------------------

class PresencaCreate(BaseModel):
    aluno_id: int
    observacoes: Optional[str] = None


class PresencaOut(BaseModel):
    id: int
    aluno_id: int
    data_hora: datetime
    observacoes: Optional[str]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Avaliação Física
# ---------------------------------------------------------------------------

class AvaliacaoCreate(BaseModel):
    aluno_id: int
    data: date
    peso_kg: Optional[Decimal] = None
    altura_cm: Optional[Decimal] = None
    gordura_percent: Optional[Decimal] = None
    massa_muscular_kg: Optional[Decimal] = None
    torax: Optional[Decimal] = None
    cintura: Optional[Decimal] = None
    quadril: Optional[Decimal] = None
    braco_dir: Optional[Decimal] = None
    braco_esq: Optional[Decimal] = None
    coxa_dir: Optional[Decimal] = None
    coxa_esq: Optional[Decimal] = None
    panturrilha_dir: Optional[Decimal] = None
    panturrilha_esq: Optional[Decimal] = None
    observacoes: Optional[str] = None


class AvaliacaoOut(AvaliacaoCreate):
    id: int
    imc: Optional[Decimal]
    criado_em: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Exercícios
# ---------------------------------------------------------------------------

class ExercicioCreate(BaseModel):
    nome: str
    grupo_muscular: Optional[str] = None
    descricao: Optional[str] = None


class ExercicioOut(BaseModel):
    id: int
    nome: str
    grupo_muscular: Optional[str]
    descricao: Optional[str]
    ativo: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Treinos
# ---------------------------------------------------------------------------

class TreinoExercicioCreate(BaseModel):
    exercicio_id: int
    series: int = 3
    repeticoes: int = 12
    carga_kg: Optional[Decimal] = None
    descanso_segundos: Optional[int] = 60
    observacoes: Optional[str] = None
    ordem: int = 1


class TreinoExercicioOut(TreinoExercicioCreate):
    id: int
    exercicio: ExercicioOut

    model_config = {"from_attributes": True}


class TreinoCreate(BaseModel):
    aluno_id: int
    professor_id: Optional[int] = None
    identificador: str = "A"
    nome: Optional[str] = None
    objetivo: Optional[str] = None
    data_inicio: Optional[date] = None
    data_validade: Optional[date] = None
    exercicios: List[TreinoExercicioCreate] = []


class TreinoOut(BaseModel):
    id: int
    aluno_id: int
    professor_id: Optional[int]
    identificador: str
    nome: Optional[str]
    objetivo: Optional[str]
    data_inicio: Optional[date]
    data_validade: Optional[date]
    ativo: bool
    exercicios: List[TreinoExercicioOut]
    criado_em: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Aulas Coletivas
# ---------------------------------------------------------------------------

class AulaCreate(BaseModel):
    nome: str
    professor_id: Optional[int] = None
    dia_semana: DiaSemana
    horario_inicio: str  # HH:MM
    horario_fim: str
    capacidade_maxima: int = 20


class AulaOut(BaseModel):
    id: int
    nome: str
    professor_id: Optional[int]
    dia_semana: DiaSemana
    horario_inicio: time_type
    horario_fim: time_type
    capacidade_maxima: int
    ativa: bool
    vagas_disponiveis: Optional[int] = None

    model_config = {"from_attributes": True}


class InscricaoCreate(BaseModel):
    aluno_id: int
    aula_id: int


class InscricaoOut(BaseModel):
    id: int
    aluno_id: int
    aula_id: int
    status: InscricaoStatus
    data_inscricao: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardOut(BaseModel):
    total_alunos_ativos: int
    total_alunos_inativos: int
    checkins_hoje: int
    mensalidades_em_atraso: int
    receita_mes_atual: Decimal
    alunos_sem_treino: int
    avaliacoes_mes_atual: int
