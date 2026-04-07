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
