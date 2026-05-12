from fastapi import Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_token
from app.core.security import decode_token
from app.models.public import AccessLog, AuditLog


def _extract_actor(request: Request) -> dict:
    token = get_current_token(request)
    if not token:
        return {}
    payload = decode_token(token) or {}
    return {
        "actor_id": str(payload.get("sub")) if payload.get("sub") is not None else None,
        "actor_scope": payload.get("scope"),
        "actor_role": payload.get("role"),
        "schema_name": payload.get("schema"),
    }


def registrar_auditoria(
    request: Request,
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: str | None = None,
):
    actor = _extract_actor(request)
    ip = request.client.host if request.client else None
    try:
        db.add(
            AuditLog(
                actor_id=actor.get("actor_id"),
                actor_scope=actor.get("actor_scope"),
                actor_role=actor.get("actor_role"),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                schema_name=actor.get("schema_name"),
                details=details,
                ip=ip,
            )
        )
        db.commit()
    except Exception:
        db.rollback()


def registrar_acesso(
    request: Request,
    db: Session,
    status_code: int,
    duration_ms: int | None = None,
):
    actor = _extract_actor(request)
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    path = request.url.path

    try:
        db.add(
            AccessLog(
                method=request.method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                actor_id=actor.get("actor_id"),
                actor_scope=actor.get("actor_scope"),
                actor_role=actor.get("actor_role"),
                schema_name=actor.get("schema_name"),
                ip=ip,
                user_agent=user_agent,
            )
        )
        db.commit()
    except Exception:
        db.rollback()


def obter_ultimas_alteracoes(
    db: Session,
    resource_type: str,
    resource_id: str,
    limit: int = 2,
):
    try:
        return (
            db.query(AuditLog)
            .filter(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == str(resource_id),
            )
            .order_by(AuditLog.criado_em.desc())
            .limit(limit)
            .all()
        )
    except Exception:
        return []


def obter_ultimas_alteracoes_por_recursos(
    db: Session,
    resource_type: str,
    resource_ids: list[str],
):
    if not resource_ids:
        return {}
    try:
        rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id.in_(resource_ids),
            )
            .order_by(AuditLog.resource_id.asc(), AuditLog.criado_em.desc())
            .all()
        )
    except Exception:
        return {}
    out = {}
    for row in rows:
        rid = str(row.resource_id)
        if rid not in out:
            out[rid] = []
        if len(out[rid]) < 2:
            out[rid].append(row)
    return out
