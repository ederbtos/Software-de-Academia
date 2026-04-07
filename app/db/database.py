from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, poolclass=NullPool)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_db(schema: str):
    """Retorna uma sessão com search_path definido para o schema do tenant."""
    db = SessionLocal()
    db.execute(text(f'SET search_path TO "{schema}", public'))
    try:
        yield db
    finally:
        db.close()


def create_tenant_schema(schema: str, db: Session):
    """Cria o schema do tenant e todas as tabelas necessárias."""
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    db.execute(text(f'SET search_path TO "{schema}", public'))
    db.commit()

    from app.models import tenant as tenant_models  # noqa: F401
    from app.db.database import Base

    # Cria tabelas no schema do tenant usando a engine com search_path
    with engine.connect() as conn:
        conn.execute(text(f'SET search_path TO "{schema}", public'))
        Base.metadata.create_all(bind=conn, tables=[
            t for name, t in Base.metadata.tables.items()
            if not name.startswith("public.")
        ])
        conn.commit()
