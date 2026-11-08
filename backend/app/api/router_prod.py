from fastapi import APIRouter

# Producción free (512 MB): rutas del producto completo; pronóstico desde Supabase, no joblib en RAM.
from app.api.routes.auth_demo import router as auth_demo_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.chat import router as chat_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.signals import router as signals_router
from app.api.routes.endemic import router as endemic_router
from app.api.routes.report import router as report_router
from app.api.routes.realtime import router as realtime_router
from app.api.routes.mobility import router as mobility_router
from app.api.routes.timeseries import router as timeseries_router
from app.api.routes.trends import router as trends_router
from app.api.routes.news import router as news_router
from app.api.routes.whatif import router as whatif_router
from app.api.routes.anova import router as anova_router
from app.api.routes.weather import router as weather_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])

api_prefixes = ["/api", "/api/v1", "/api/v3"]

routers = [
    (auth_demo_router, "auth"),
    (chat_router, "chat"),
    (history_router, "history"),
    (alerts_router, "alerts"),
    (signals_router, "signals"),
    (endemic_router, "endemic"),
    (report_router, "report"),
    (mobility_router, "mobility"),
    (timeseries_router, "timeseries"),
    (trends_router, "trends"),
    (news_router, "news"),
    (whatif_router, "whatif"),
    (anova_router, "anova"),
    (weather_router, "weather"),
]

for prefix in api_prefixes:
    for r, tag in routers:
        api_router.include_router(r, prefix=prefix, tags=[tag])

api_router.include_router(realtime_router, tags=["realtime"])
