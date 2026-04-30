from fastapi import Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_token
from app.core.security import decode_token
from app.models.public import AuditLog


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
