"""Comprobación de orígenes y cabeceras CORS de respaldo (Vercel previews)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

_VERCEL_PREVIEW = re.compile(r"^https://.+\.vercel\.app$", re.IGNORECASE)


def origin_is_allowed(origin: str) -> bool:
    from app.core.config import settings

    if not origin:
        return False
    origin = origin.rstrip("/")
    if origin in settings.resolved_cors_origins:
        return True
    pat = settings.resolved_cors_origin_regex
    if pat:
        try:
            if re.fullmatch(pat, origin, flags=re.IGNORECASE):
                return True
        except re.error:
            pass
    return bool(_VERCEL_PREVIEW.fullmatch(origin))


def apply_cors_headers(request: Request, response: Response) -> None:
    origin = request.headers.get("origin", "")
    if not origin_is_allowed(origin):
        return
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    vary = response.headers.get("vary", "")
    if "origin" not in vary.lower():
        response.headers["Vary"] = f"{vary}, Origin".strip(", ")
