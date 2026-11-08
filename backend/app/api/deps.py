from fastapi import Header, HTTPException

from app.core.config import settings
from app.services.chat_demo_auth import verify_token


def require_demo_chat_auth(authorization: str | None = Header(default=None)) -> str | None:
    if not settings.chat_demo_auth_required:
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Inicia sesión para usar el asistente IA.")
    token = authorization[7:].strip()
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Sesión expirada. Vuelve a iniciar sesión.")
    return username
