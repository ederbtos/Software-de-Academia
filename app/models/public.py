"""
Models do schema public (core do sistema).
Usados pelo superadmin para gerenciar academias e planos globais.
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum, Integer, Numeric, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class AcademiaStatus(str, enum.Enum):
    ativa = "ativa"
    inativa = "inativa"
    suspensa = "suspensa"


class Academia(Base):
    __tablename__ = "academias"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    slug = Column(String(60), unique=True, nullable=False, index=True)  # subdomínio
    cnpj = Column(String(18), unique=True, nullable=True)
    telefone = Column(String(20), nullable=True)
    email = Column(String(120), nullable=True)
    endereco = Column(Text, nullable=True)
    status = Column(Enum(AcademiaStatus), default=AcademiaStatus.ativa)
    schema_name = Column(String(80), nullable=False)  # ex: academia_fitclub
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuarios = relationship("UsuarioPublic", back_populates="academia")


class UsuarioPublicRole(str, enum.Enum):
    superadmin = "superadmin"
    admin_academia = "admin_academia"


class UsuarioPublic(Base):
    """Usuários no schema public: superadmins e admins de academia."""
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    role = Column(Enum(UsuarioPublicRole), default=UsuarioPublicRole.admin_academia)
    ativo = Column(Boolean, default=True)
    academia_id = Column(Integer, ForeignKey("public.academias.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    academia = relationship("Academia", back_populates="usuarios")


class PlanoGlobal(Base):
    """Planos de assinatura do sistema (definidos pelo superadmin)."""
    __tablename__ = "planos_globais"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(80), nullable=False)
    descricao = Column(Text, nullable=True)
    valor_mensal = Column(Numeric(10, 2), nullable=False)
    limite_alunos = Column(Integer, nullable=True)  # None = ilimitado
    ativo = Column(Boolean, default=True)


class PasswordResetToken(Base):
    """Tokens de recuperação de senha (público e tenant)."""
    __tablename__ = "password_reset_tokens"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), nullable=False)
    schema_name = Column(String(80), nullable=True)  # None = UsuarioPublic
    usado = Column(Boolean, default=False)
    expira_em = Column(DateTime, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
