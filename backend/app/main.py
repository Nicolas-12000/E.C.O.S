import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging(settings.debug)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_task = None
    if settings.grpc_port > 0:
        try:
            from app.grpc.serve import serve_grpc_async

            grpc_task = await serve_grpc_async(settings.grpc_port)
            logger.info("gRPC listening on port %s", settings.grpc_port)
        except Exception as exc:
            logger.warning("gRPC not started: %s", exc)
    yield
    if grpc_task:
        await grpc_task.stop(grace=None)


# Producción liviana salvo ECOS_FULL_API=true (Render 512MB vs plan con más RAM).
if settings.env == "production" and not settings.enable_full_api:
    from app.api.router_prod import api_router
else:
    from app.api.router import api_router

# Revisión / agentes: alcance, router prod vs dev y checklist → AGENTS.md y docs/REVISION_BACKEND.md
app = FastAPI(
    title="ECOS API",
    description=(
        "Early Control and Observation System — API de alerta temprana epidemiológica. "
        "Contrato OpenAPI; pronóstico servido desde corridas en Supabase (job semanal). "
        "Ver README (evaluación técnica), AGENTS.md y docs/REVISION_BACKEND.md."
    ),
    version="0.3.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS — frontend Next.js (Vercel prod + previews *.vercel.app)
_cors_regex = settings.resolved_cors_origin_regex
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.resolved_cors_origins,
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if _cors_regex:
    logger.info("CORS allow_origin_regex=%s", _cors_regex)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "name": "ECOS API",
        "version": "0.3.0",
        "status": "ok",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/ws/alerts",
            "/api/v3/predict",
            "/api/v3/history",
            "/api/v3/signals",
            "/api/v3/chat",
            "/api/v3/alerts",
            "/api/v3/endemic",
        ],
    }
