"""Token HMAC y verificación de usuarios demo (pgcrypto) para el chat IA."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any

from app.core.config import settings
from app.core.db import get_db_connection

logger = logging.getLogger(__name__)

_TOKEN_TTL_S = 12 * 3600


def _secret() -> str:
    return settings.chat_demo_token_secret or "ecos-dev-chat-demo-secret-change-me"


def issue_token(username: str) -> str:
    payload = {"sub": username, "exp": int(time.time()) + _TOKEN_TTL_S}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(_secret().encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_token(token: str) -> str | None:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(_secret().encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    pad = "=" * (-len(body) % 4)
    try:
        payload: dict[str, Any] = json.loads(base64.urlsafe_b64decode(body + pad))
    except (json.JSONDecodeError, ValueError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) and sub else None


def verify_demo_credentials(login: str, password: str) -> str | None:
    """login = username o email; devuelve username si OK."""
    login = login.strip().lower()
    if not login or not password:
        return None
    db_url = settings.resolved_database_url()
    if not db_url:
        logger.warning("demo chat auth: sin SUPABASE_DB_URL")
        return None
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT username
                    FROM demo_chat_users
                    WHERE (lower(username) = %s OR lower(email) = %s)
                      AND password_hash = crypt(%s, password_hash)
                    LIMIT 1
                    """,
                    (login, login, password),
                )
                row = cur.fetchone()
                return row[0] if row else None
    except Exception:
        logger.exception("demo chat auth: error consultando demo_chat_users")
        return None
