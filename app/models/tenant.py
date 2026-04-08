"""
Models do schema tenant (por academia).
Todas as tabelas aqui são criadas dentro do schema da academia (ex: academia_fitclub).
"""
import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Enum, Integer,
    Numeric, Text, ForeignKey, Time, SmallInteger
)
from sqlalchemy.orm import relationship
from app.db.database import Base


# ---------------------------------------------------------------------------
# Funcionários / Professores
# ---------------------------------------------------------------------------

class FuncionarioRole(str, enum.Enum):
    admin = "admin"
    professor = "professor"
    recepcionista = "recepcionista"


class Funcionario(Base):
    __tablename__ = "funcionarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    telefone = Column(String(20), nullable=True)
    role = Column(Enum(FuncionarioRole), default=FuncionarioRole.recepcionista)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    treinos = relationship("Treino", back_populates="professor")
    aulas = relationship("Aula", back_populates="professor")


# ---------------------------------------------------------------------------
# Planos da academia
# ---------------------------------------------------------------------------

class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(80), nullable=False)
    descricao = Column(Text, nullable=True)
    valor = Column(Numeric(10, 2), nullable=False)
    duracao_dias = Column(Integer, nullable=False, default=30)
    ativo = Column(Boolean, default=True)

    matriculas = relationship("Matricula", back_populates="plano")


# ---------------------------------------------------------------------------
# Alunos
# ---------------------------------------------------------------------------

class SexoEnum(str, enum.Enum):
    masculino = "masculino"
    feminino = "feminino"
    outro = "outro"


class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=True, index=True)
    cpf = Column(String(14), unique=True, nullable=True)
    telefone = Column(String(20), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    sexo = Column(Enum(SexoEnum), nullable=True)
    endereco = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    foto_url = Column(String(255), nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    matriculas = relationship("Matricula", back_populates="aluno")
    presencas = relationship("Presenca", back_populates="aluno")
    avaliacoes = relationship("AvaliacaoFisica", back_populates="aluno")
    treinos = relationship("Treino", back_populates="aluno")
    inscricoes_aulas = relationship("InscricaoAula", back_populates="aluno")
    notificacoes = relationship("Notificacao", back_populates="aluno")


# ---------------------------------------------------------------------------
# Matrículas / Mensalidades
# ---------------------------------------------------------------------------

class MatriculaStatus(str, enum.Enum):
    ativa = "ativa"
    vencida = "vencida"
    cancelada = "cancelada"


class Matricula(Base):
    __tablename__ = "matriculas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    plano_id = Column(Integer, ForeignKey("planos.id"), nullable=False)
    data_inicio = Column(Date, nullable=False, default=date.today)
    data_vencimento = Column(Date, nullable=False)
    status = Column(Enum(MatriculaStatus), default=MatriculaStatus.ativa)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    aluno = relationship("Aluno", back_populates="matriculas")
    plano = relationship("Plano", back_populates="matriculas")
    pagamentos = relationship("Pagamento", back_populates="matricula")


class PagamentoStatus(str, enum.Enum):
    pendente = "pendente"
    pago = "pago"
    cancelado = "cancelado"


class PagamentoMetodo(str, enum.Enum):
    dinheiro = "dinheiro"
    cartao_credito = "cartao_credito"
    cartao_debito = "cartao_debito"
    pix = "pix"
    transferencia = "transferencia"


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    matricula_id = Column(Integer, ForeignKey("matriculas.id"), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    data_vencimento = Column(Date, nullable=False)
    data_pagamento = Column(Date, nullable=True)
    status = Column(Enum(PagamentoStatus), default=PagamentoStatus.pendente)
    metodo = Column(Enum(PagamentoMetodo), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    matricula = relationship("Matricula", back_populates="pagamentos")


# ---------------------------------------------------------------------------
# Presença (check-in)
# ---------------------------------------------------------------------------

class Presenca(Base):
    __tablename__ = "presencas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    data_hora = Column(DateTime, default=datetime.utcnow, nullable=False)
    observacoes = Column(String(255), nullable=True)

    aluno = relationship("Aluno", back_populates="presencas")


# ---------------------------------------------------------------------------
# Avaliação Física
# ---------------------------------------------------------------------------

class AvaliacaoFisica(Base):
    __tablename__ = "avaliacoes_fisicas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    data = Column(Date, nullable=False, default=date.today)
    peso_kg = Column(Numeric(5, 2), nullable=True)
    altura_cm = Column(Numeric(5, 1), nullable=True)
    imc = Column(Numeric(4, 2), nullable=True)
    gordura_percent = Column(Numeric(4, 2), nullable=True)
    massa_muscular_kg = Column(Numeric(5, 2), nullable=True)
    # Medidas (cm)
    torax = Column(Numeric(5, 1), nullable=True)
    cintura = Column(Numeric(5, 1), nullable=True)
    quadril = Column(Numeric(5, 1), nullable=True)
    braco_dir = Column(Numeric(5, 1), nullable=True)
    braco_esq = Column(Numeric(5, 1), nullable=True)
    coxa_dir = Column(Numeric(5, 1), nullable=True)
    coxa_esq = Column(Numeric(5, 1), nullable=True)
    panturrilha_dir = Column(Numeric(5, 1), nullable=True)
    panturrilha_esq = Column(Numeric(5, 1), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    aluno = relationship("Aluno", back_populates="avaliacoes")


# ---------------------------------------------------------------------------
# Treinos
# ---------------------------------------------------------------------------

class Treino(Base):
    __tablename__ = "treinos"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    professor_id = Column(Integer, ForeignKey("funcionarios.id"), nullable=True)
    identificador = Column(String(10), nullable=False, default="A")  # A, B, C etc.
    nome = Column(String(120), nullable=True)
    objetivo = Column(String(120), nullable=True)
    data_inicio = Column(Date, nullable=True)
    data_validade = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    aluno = relationship("Aluno", back_populates="treinos")
    professor = relationship("Funcionario", back_populates="treinos")
    exercicios = relationship("TreinoExercicio", back_populates="treino", cascade="all, delete-orphan")


class Exercicio(Base):
    """Biblioteca de exercícios da academia."""
    __tablename__ = "exercicios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    grupo_muscular = Column(String(80), nullable=True)
    descricao = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)

    treino_exercicios = relationship("TreinoExercicio", back_populates="exercicio")


class TreinoExercicio(Base):
    __tablename__ = "treino_exercicios"

    id = Column(Integer, primary_key=True, index=True)
    treino_id = Column(Integer, ForeignKey("treinos.id"), nullable=False)
    exercicio_id = Column(Integer, ForeignKey("exercicios.id"), nullable=False)
    series = Column(SmallInteger, nullable=False, default=3)
    repeticoes = Column(SmallInteger, nullable=False, default=12)
    carga_kg = Column(Numeric(5, 2), nullable=True)
    descanso_segundos = Column(SmallInteger, nullable=True, default=60)
    observacoes = Column(Text, nullable=True)
    ordem = Column(SmallInteger, nullable=False, default=1)

    treino = relationship("Treino", back_populates="exercicios")
    exercicio = relationship("Exercicio", back_populates="treino_exercicios")


# ---------------------------------------------------------------------------
# Aulas Coletivas
# ---------------------------------------------------------------------------

class DiaSemana(str, enum.Enum):
    segunda = "segunda"
    terca = "terca"
    quarta = "quarta"
    quinta = "quinta"
    sexta = "sexta"
    sabado = "sabado"
    domingo = "domingo"


class Aula(Base):
    __tablename__ = "aulas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    professor_id = Column(Integer, ForeignKey("funcionarios.id"), nullable=True)
    dia_semana = Column(Enum(DiaSemana), nullable=False)
    horario_inicio = Column(Time, nullable=False)
    horario_fim = Column(Time, nullable=False)
    capacidade_maxima = Column(Integer, nullable=False, default=20)
    ativa = Column(Boolean, default=True)

    professor = relationship("Funcionario", back_populates="aulas")
    inscricoes = relationship("InscricaoAula", back_populates="aula")


class InscricaoStatus(str, enum.Enum):
    confirmada = "confirmada"
    lista_espera = "lista_espera"
    cancelada = "cancelada"


class InscricaoAula(Base):
    __tablename__ = "inscricoes_aulas"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    aula_id = Column(Integer, ForeignKey("aulas.id"), nullable=False)
    data_inscricao = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(InscricaoStatus), default=InscricaoStatus.confirmada)

    aluno = relationship("Aluno", back_populates="inscricoes_aulas")
    aula = relationship("Aula", back_populates="inscricoes")


# ---------------------------------------------------------------------------
# Notificações
# ---------------------------------------------------------------------------

class NotificacaoTipo(str, enum.Enum):
    vencimento_plano = "vencimento_plano"
    mensalidade_atrasada = "mensalidade_atrasada"
    aviso_geral = "aviso_geral"
    treino_inativo = "treino_inativo"


class NotificacaoStatus(str, enum.Enum):
    pendente = "pendente"
    enviada = "enviada"
    falha = "falha"


class Notificacao(Base):
    __tablename__ = "notificacoes"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=True)
    tipo = Column(Enum(NotificacaoTipo), nullable=False)
    titulo = Column(String(120), nullable=False)
    mensagem = Column(Text, nullable=False)
    status = Column(Enum(NotificacaoStatus), default=NotificacaoStatus.pendente)
    criado_em = Column(DateTime, default=datetime.utcnow)
    enviado_em = Column(DateTime, nullable=True)

    aluno = relationship("Aluno", back_populates="notificacoes")
