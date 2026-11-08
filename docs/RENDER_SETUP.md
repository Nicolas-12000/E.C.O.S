# Render — New Web Service (monorepo E.C.O.S)

Copia esto en el formulario de Render al conectar `Nicolas-12000/E.C.O.S`.

## Campos del formulario

| Campo | Valor |
|--------|--------|
| **Name** | `ecos-api` (o `E-COS-api`; evita puntos en el hostname) |
| **Project** | My project → Production |
| **Language** | Python 3 |
| **Branch** | `main` |
| **Region** | Oregon (US West) |
| **Root Directory** | `backend` |
| **Build Command** | `pip install -r ../requirements-prod-minimal.txt` |
| **Start Command** | ver abajo |
| **Compute (free)** | 512 MB — chat + alertas + WS |
| **Compute (completo)** | **1 CPU / 2 GB** + `ECOS_FULL_API=true` + `requirements-prod.txt` |

### Start Command (recomendado)

Free / 512 MB (1 worker):

```bash
hypercorn app.main:app --config hypercorn.toml --bind 0.0.0.0:$PORT
```

Añade en env: `ECOS_ASGI_SERVER=hypercorn`

### HTTP/2 en free tier (cómo contarlo en clase)

| Tramo | Protocolo |
|-------|-----------|
| Navegador ↔ `*.onrender.com` | **HTTPS**; el borde suele negociar **HTTP/2** (multiplexación) |
| Proxy Render ↔ tu contenedor | **HTTP/1.1** (no metes TLS ni h2 dentro del dyno) |
| Dentro del contenedor | **Hypercorn** (asyncio, 1 worker): REST + **WebSocket** en el mismo proceso |
| gRPC | **Apagado** (`GRPC_PORT=0`); local sí con Protobuf sobre h2 |

No hace falta certificado en el app: el HTTP/2 “visible” es el del **edge**. Hypercorn sustituye a gunicorn+uvicorn para menos RAM y WS estable en 512 MB.

Fallback local:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Variables de entorno (Environment)

Obligatorias en Render:

| Key | Value |
|-----|--------|
| `ENV` | `production` |
| `DEBUG` | `false` |
| `GROQ_API_KEY` | (secret — Groq console) |
| `GROQ_MODEL` | `openai/gpt-oss-120b` |
| `SUPABASE_DB_URL` | `postgresql://…` (Session / Direct de Supabase) |
| `CORS_ORIGINS` | `https://TU-APP.vercel.app,http://localhost:3000` (coma, **sin** JSON) — o **borrar** la variable (previews usan regex `*.vercel.app`) |
| `CORS_ALLOW_VERCEL` | `true` (default) — permite **previews** `https://….vercel.app` vía regex |
| `CHAT_DEMO_AUTH_REQUIRED` | `true` (login obligatorio para `/chat`; migración `0007`) |
| `CHAT_DEMO_TOKEN_SECRET` | string aleatorio largo (opcional; si no, usa default interno) |

Opcionales:

| Key | Value |
|-----|--------|
| `ECOS_FULL_API` | `true` → pronóstico, what-if, movilidad, tendencias (necesita más RAM; ver abajo) |
| `GRPC_PORT` | `0` en Render (gRPC solo local/LAN; HTTP público usa REST + `/ws/alerts`) |
| `SUPABASE_URL` | URL proyecto Supabase |
| `SUPABASE_ANON_KEY` | anon key |
| `DATABASE_URL` | alias de Postgres si no usas `SUPABASE_DB_URL` |
| `OPENWEATHER_API_KEY` | clima en chat |

**No pegues** “Add from `.env`” en el repo si `.env` está en gitignore: copia manual desde tu `.env` local.

## Perfiles de deploy

### A) Free 512 MB — producto **completo en UI** (recomendado)

- Build: `requirements-prod-minimal.txt`
- `ECOS_FULL_API` = `false` (o no definido)
- **Todas las pantallas** (alertas, pronóstico, mapa, tendencias, noticias, ANOVA, chat, WS)
- Pronóstico y alertas leen **`prediction_runs` / `prediction_points` en Supabase** (no joblib en RAM)
- What-if con sliders: **503** en free — lista escenarios guardados sí funciona; simulación en vivo requiere B
- **Imprescindible antes del deploy:** migraciones Supabase + `python scripts/weekly_forecast_job.py` (en tu PC)
- Front: Vercel `NEXT_PUBLIC_API_URL=https://TU-SERVICIO.onrender.com`

### B) Producto completo

- Plan **≥ 1 GB** (recomendado 2 GB)
- Build: `pip install -r ../requirements-prod.txt`
- `ECOS_FULL_API=true`
- Sube `models/*.joblib` en el repo (hijo `ecos-api`) o persistent disk

## Vercel (front)

| Campo | Valor |
|--------|--------|
| Root Directory | `frontend` |
| `NEXT_PUBLIC_API_URL` | `https://TU-SERVICIO.onrender.com` (sin `/` final) |

Tras el primer deploy, pega la URL real en `CORS_ORIGINS`.

## Verificación

1. `GET https://…onrender.com/` → `status: ok`
2. `GET /docs` → OpenAPI (contract-first)
3. `wss://…onrender.com/ws/alerts` (desde `/alertas` en Vercel)
4. `POST /api/v1/chat` con pregunta de prueba

## gRPC local (HTTP/2 + Protobuf)

```bash
pip install grpcio grpcio-tools
./scripts/generate_grpc.sh
cd backend
GRPC_PORT=50051 ECOS_FULL_API=true uvicorn app.main:app --reload
# otro terminal: grpcurl -plaintext localhost:50051 ecos.v1.ForecastService/Health
```

En Render **no** expongas `GRPC_PORT`: el balanceador solo publica `$PORT` HTTP.
