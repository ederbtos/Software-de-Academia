from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.public import AcademiaStatus, UsuarioPublicRole


class AcademiaCreate(BaseModel):
    nome: str
    slug: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco: Optional[str] = None


class AcademiaUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco: Optional[str] = None
    status: Optional[AcademiaStatus] = None


class AcademiaOut(BaseModel):
    id: int
    nome: str
    slug: str
    cnpj: Optional[str]
    telefone: Optional[str]
    email: Optional[str]
    endereco: Optional[str]
    status: AcademiaStatus
    schema_name: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class UsuarioPublicCreate(BaseModel):
    nome: str
    email: EmailStr
    password: str
    role: UsuarioPublicRole = UsuarioPublicRole.admin_academia
    academia_id: Optional[int] = None


class UsuarioPublicOut(BaseModel):
    id: int
    nome: str
    email: str
    role: UsuarioPublicRole
    ativo: bool
    academia_id: Optional[int]

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    academia_slug: Optional[str] = None


class AuditLogOut(BaseModel):
    id: int
    actor_id: Optional[str]
    actor_scope: Optional[str]
    actor_role: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    schema_name: Optional[str]
    details: Optional[str]
    ip: Optional[str]
    criado_em: datetime

    model_config = {"from_attributes": True}


class AuditMetricaItem(BaseModel):
    chave: str
    total: int


class AuditVolumeDiaItem(BaseModel):
    dia: str
    total: int


class AuditMetricasOut(BaseModel):
    total_eventos: int
    top_acoes: list[AuditMetricaItem]
    top_atores: list[AuditMetricaItem]
    volume_diario: list[AuditVolumeDiaItem]
