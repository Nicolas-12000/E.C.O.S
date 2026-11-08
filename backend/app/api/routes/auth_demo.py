from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.chat_demo_auth import issue_token, verify_demo_credentials

router = APIRouter()


class DemoLoginRequest(BaseModel):
    login: str = Field(..., min_length=1, description="Usuario o correo demo")
    password: str = Field(..., min_length=1)


class DemoLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    email: str


class DemoHintResponse(BaseModel):
    hint: str
    email: str
    username: str


@router.get("/auth/demo-hint", response_model=DemoHintResponse, summary="Pista pública (sin contraseña)")
def demo_hint():
    return DemoHintResponse(
        hint="Vuelta en Baviera, abril 2026 — marcador del partido",
        email="camavinga@allianz2026.ecos",
        username="camavinga",
    )


@router.post("/auth/demo-login", response_model=DemoLoginResponse, summary="Login demo asistente IA")
def demo_login(req: DemoLoginRequest):
    if not settings.chat_demo_auth_required:
        return DemoLoginResponse(
            access_token=issue_token("guest"),
            username="guest",
            email="guest@ecos",
        )
    username = verify_demo_credentials(req.login, req.password)
    if not username:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    email = req.login if "@" in req.login else f"{username}@allianz2026.ecos"
    if username == "camavinga":
        email = "camavinga@allianz2026.ecos"
    return DemoLoginResponse(
        access_token=issue_token(username),
        username=username,
        email=email,
    )
