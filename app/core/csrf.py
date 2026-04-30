import secrets
from fastapi import HTTPException, Request, status


CSRF_COOKIE_NAME = "csrf_token"
CSRF_FIELD_NAME = "csrf_token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


async def validate_csrf(request: Request) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    form_token = None

    header_token = request.headers.get("x-csrf-token")
    if header_token:
        form_token = header_token
    else:
        ctype = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
            form = await request.form()
            form_token = form.get(CSRF_FIELD_NAME)

    if not cookie_token or not form_token or cookie_token != form_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token inválido. Recarregue a página e tente novamente.",
        )
