import re
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status
from app.models.public import Academia, AcademiaStatus, UsuarioPublic, UsuarioPublicRole
from app.models import tenant as tenant_models
from app.schemas.public import AcademiaCreate, AcademiaUpdate, UsuarioPublicCreate
from app.core.security import hash_password
from app.db.database import engine, Base


def _slug_valido(slug: str) -> bool:
    return bool(re.match(r"^[a-z0-9-]{3,60}$", slug))


def listar_academias(db: Session):
    return db.query(Academia).all()


def criar_academia(data: AcademiaCreate, db: Session) -> Academia:
    if not _slug_valido(data.slug):
        raise HTTPException(status_code=400, detail="Slug inválido. Use apenas letras minúsculas, números e hífens (3-60 chars).")
    if db.query(Academia).filter(Academia.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="Slug já em uso")

    schema_name = f"academia_{data.slug.replace('-', '_')}"

    academia = Academia(
        nome=data.nome,
        slug=data.slug,
        cnpj=data.cnpj,
        telefone=data.telefone,
        email=data.email,
        endereco=data.endereco,
        schema_name=schema_name,
        status=AcademiaStatus.ativa,
    )
    db.add(academia)
    db.flush()

    # Cria o schema e todas as tabelas tenant
    _provisionar_schema(schema_name, db)

    db.commit()
    db.refresh(academia)
    return academia


def _provisionar_schema(schema_name: str, db: Session):
    """Cria o schema PostgreSQL e todas as tabelas do tenant."""
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    db.commit()

    # Recria engine com search_path para criar tabelas no schema correto
    with engine.connect() as conn:
        conn.execute(text(f'SET search_path TO "{schema_name}", public'))
        # Cria apenas tabelas sem schema explícito (tabelas tenant)
        tenant_tables = [
            t for name, t in Base.metadata.tables.items()
            if "." not in name  # tabelas sem schema explícito = tenant
        ]
        Base.metadata.create_all(bind=conn, tables=tenant_tables)
        conn.commit()


def atualizar_academia(academia_id: int, data: AcademiaUpdate, db: Session) -> Academia:
    academia = db.query(Academia).filter(Academia.id == academia_id).first()
    if not academia:
        raise HTTPException(status_code=404, detail="Academia não encontrada")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(academia, field, value)
    db.commit()
    db.refresh(academia)
    return academia


def criar_usuario_publico(data: UsuarioPublicCreate, db: Session) -> UsuarioPublic:
    if db.query(UsuarioPublic).filter(UsuarioPublic.email == data.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    user = UsuarioPublic(
        nome=data.nome,
        email=data.email,
        senha_hash=hash_password(data.password),
        role=data.role,
        academia_id=data.academia_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
