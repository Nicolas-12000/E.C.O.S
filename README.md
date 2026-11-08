# ECOS — Early Control and Observation System

Sistema de vigilancia y anticipación epidemiológica para **Colombia** (dengue, malaria, zika, chikungunya). Integra datos oficiales (SIVIGILA), clima, movilidad, búsquedas y medios; expone un **dashboard**, **alertas con horizonte 1–4 semanas** y un **asistente conversacional** anclado a la misma base curada en **Supabase**.

---

## Qué hace el producto (en una mirada)

| Módulo | Función |
|--------|---------|
| **Dashboard / movilidad** | Mapas y flujos origen–destino ligados a casos |
| **Alertas & pronóstico** | Prioriza municipios según corrida semanal o último corte observado |
| **What-if** | Contrafactual de variables exógenas (vacunación, movilidad, clima, trends, noticias) con modelo híbrido cuando hay artefactos |
| **Tendencias & noticias** | Señales tempranas (Trends, RSS) |
| **ANOVA** | Contraste multianual con inferencia estadística (SciPy) |
| **Chat ECOS** | Consultas en lenguaje natural; respuestas con datos SQL + Groq, sin inventar cifras en modo outlook |

El **modelo servido** (naive / Ridge / híbrido) se elige con `models/metrics.json`: solo se defiende el híbrido si no pierde frente a Ridge en MAE. En producción liviana, el pronóstico se **lee desde Supabase** (`prediction_runs` / `prediction_points`) tras ejecutar el job semanal en tu máquina.

---

## Arquitectura (cómo encaja todo)

```
[ Fuentes: SIVIGILA, clima, movilidad, RSS, Trends ]
           │
           ▼  Spark / scripts (ecos-data)
[ Bronze → Silver → Gold → Supabase Postgres ]
           │
           ▼  weekly_forecast_job (operación, no el request del usuario)
[ prediction_points ] ─────────────────────────┐
           │                                    │
           ▼                                    ▼
[ FastAPI — Hypercorn ASGI ]  ◄── REST / OpenAPI    WebSocket /ws/alerts
           │                      JSON               (tiempo real)
           │ optional: gRPC ForecastService (Protobuf, HTTP/2) si GRPC_PORT>0
           ▼
[ Next.js en Vercel ] — CSR, Web Worker (agregaciones), Service Worker (shell), Zod en ticks WS
```

**Monorepo** = desarrollo diario. Opcionalmente se publican **repos hijos** (`ecos-api`, `ecos-data`, `ecos-front`) con historial filtrado: ver `docs/CHILD_REPOS.md` y `scripts/export_child_repos.sh`.

---

## Decisiones de diseño (y por qué)

1. **Contract-first**  
   - REST: esquemas Pydantic + **OpenAPI** en `/docs` (SSOT para el front).  
   - Simulación/pronóstico: **`proto/ecos_forecast.proto`** + servicio gRPC (`ForecastService/WhatIf`) alineado al mismo dominio que `POST /api/v3/whatif`.

2. **RPC**  
   El navegador consume **REST + WebSocket**. gRPC vive como capa de **procedimiento remoto binario** (Protobuf) para pronóstico/what-if; en **Render free** `GRPC_PORT=0` y el canal público es HTTP. En defensa o local: `GRPC_PORT=50051` + `grpcurl`. Así se separa *experiencia web* de *contrato de servicio ML*.

3. **HTTP/2 en free tier**  
   - Cliente ↔ Render/Vercel: **HTTPS con HTTP/2 (o h3) en el borde**.  
   - Proxy ↔ contenedor: HTTP/1.1 típico en plan gratuito.  
   - Origen: **Hypercorn** (`backend/hypercorn.toml`), un worker asyncio — REST y WS en el mismo proceso, ~512 MB RAM.

4. **Tiempo real sin bloquear el main thread**  
   - **WebSocket** con resumen de alertas y revalidación SWR.  
   - **Web Worker** + `postMessage` para agregar alertas en `/alertas` (mejor **INP**).  
   - **SharedWorker** opcional: sincroniza filtros entre pestañas.  
   - Validación **runtime** de mensajes WS con **Zod** (TypeScript no basta en el wire).

5. **Datos como fuente de verdad**  
   Gold con contrato validable; Supabase canónico en demo cloud. El chat en modo *“cómo estará hoy”* usa semana epidemiológica actual y **un solo %** vs el último año en BD — sin alucinar brotes.

6. **Simulación “completa” vs deploy free**  
   Variables exógenas entran en el **híbrido** (`adjustments`). Ridge = lags lineales. En Render free: UI casi completa + pronóstico desde BD; sliders what-if en vivo piden plan con más RAM (`ECOS_FULL_API=true`) o API local con joblib.

---

## Qué necesitas descargar / instalar

| Herramienta | Uso |
|-------------|-----|
| **Git** | Clonar el repo |
| **Python 3.11+** | API y scripts |
| **Node.js 20+** | Frontend |
| **Cuenta Supabase** | Postgres + datos curados |
| **Groq API key** | Chat / RAG |
| *(Opcional)* Docker | Spark / pipeline grande |
| *(Opcional)* `grpcio-tools`, `grpcurl` | Demo gRPC en local |

### Clonar y entorno

```bash
git clone https://github.com/Nicolas-12000/E.C.O.S.git
cd E.C.O.S   # o la carpeta local ECOS

cp .env.example .env
# Editar: SUPABASE_DB_URL, GROQ_API_KEY
```

### Backend (desarrollo)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Migraciones (una vez)
python scripts/migrate_supabase.py

cd backend
uvicorn app.main:app --reload
# http://127.0.0.1:8000 — OpenAPI: /docs — health: /health
```

**Producción local con Hypercorn + gRPC opcional:**

```bash
cd backend
GRPC_PORT=50051 hypercorn app.main:app --config hypercorn.toml --bind 0.0.0.0:8000
```

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
npm run dev
# http://localhost:3000
```

### Datos y pronóstico (para que alertas/pronóstico “tengan vida”)

```bash
# Con datos ya cargados en Supabase, generar corridas:
python scripts/weekly_forecast_job.py --limit 200

# Validar contrato gold (recomendado):
python scripts/validate_gold_contract.py --supabase
```

Pipeline desde cero: ver `scripts/README.md` y `data/README.md`.

---

## Despliegue (free tier “completo”)

| Servicio | Dónde | Notas |
|----------|--------|--------|
| **API** | [Render](https://render.com) | Root `backend`, build `pip install -r ../requirements-prod-minimal.txt`, start Hypercorn — guía **`docs/RENDER_SETUP.md`** |
| **Web** | [Vercel](https://vercel.com) | Root `frontend`, `NEXT_PUBLIC_API_URL=https://tu-api.onrender.com` |
| **BD** | Supabase | `SUPABASE_DB_URL` en Render |

Variables clave en Render: `ENV=production`, `DEBUG=false`, `GROQ_API_KEY`, `SUPABASE_DB_URL`, `CORS_ORIGINS`, `GRPC_PORT=0`, `ECOS_FULL_API=false` (producto amplio leyendo pronóstico de BD).

---

## Estructura del repositorio

```
backend/          FastAPI, chat, gRPC, WS
frontend/         Next.js, workers, SW
data/             Bronze / silver / gold
models/           joblib, metrics.json
proto/            ecos_forecast.proto (gRPC)
scripts/          migrate, curate, weekly job, export_child_repos
supabase/         migraciones SQL
docs/             REVISION_BACKEND.md, RENDER_SETUP.md, CHILD_REPOS.md, WEB_RUNTIME.md, plan
AGENTS.md         Guía para revisión asistida (raíz del repo)
```

---

## Evaluación técnica (referencia rápida)

Si revisas este proyecto con criterios de **arquitectura web** o **MLOps ligero** (incluida revisión asistida por agentes), usa primero las **evidencias del repo**, no supuestos de stack:

| Paso | Acción |
|------|--------|
| 1 | Leer “Arquitectura” y “Decisiones de diseño” (arriba) — define batch vs request y prod free vs full. |
| 2 | `cd backend && pytest tests -q` (mismo comando que CI en `.github/workflows/ci.yml`). |
| 3 | Inspeccionar OpenAPI en `/docs` o `backend/app/api/router.py` / `router_prod.py`. |
| 4 | Cruzar entregables con `docs/PLAN_PROGRESS.md` y el mapa en **`docs/REVISION_BACKEND.md`**. |
| 5 | Agentes: leer también **`AGENTS.md`** (alcance, falsos negativos frecuentes). |

**Backend en este diseño** = FastAPI con dominio epidemiológico completo en código (`routes/` + `services/`), pronóstico **operativo vía Supabase + job semanal**, WebSocket de alertas, chat anclado a datos, y tests automatizados. En Render free, `router_prod` omite rutas pesadas (`predict`/`scraping` en vivo) de forma documentada; eso no equivale a “sin backend de pronóstico”.

Puntos fuertes a contrastar con la rúbrica:

- Separación **CSR + API stateless + BD + jobs batch** (no confundir request HTTP con entrenamiento).
- **Doble contrato** REST/OpenAPI y Protobuf/gRPC sobre el mismo caso de uso.
- **Workers / WS / validación runtime** en el front como optimización medible (INP, no bloqueo del event loop).
- **Trade-offs explícitos** del plan gratuito (HTTP/2 en borde, sin joblib en RAM, what-if en vivo acotado).
- Código de chat y alertas que **prioriza datos observables** frente a narrativa LLM.

---

## Licencia

MIT — ver `LICENSE` si aplica; datos terceros sujetos a sus licencias (datos abiertos Colombia, etc.).

---

**Equipo ECOS** · Observatorio epidemiológico · Colombia
