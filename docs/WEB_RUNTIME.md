# Runtime web (ECOS)

Piezas del curso (workers, WS, caché) usadas con propósito en la app.

## Simulación what-if

- Variables: vacunación, movilidad (in/out/índice), Google Trends, RSS, clima.
- Solo el **modelo híbrido** aplica deltas en features (`prediction.py` fuerza híbrido si hay `adjustments`).
- El **Ridge** sigue siendo solo lags + semana; no simula señales externas.

## Web Worker (`workers/epi-aggregate.worker.ts`)

- En `/alertas`, agrupa municipios por enfermedad **fuera del main thread** (mejor INP al filtrar listas grandes).
- Comunicación: `postMessage`; si `crossOriginIsolated`, suma casos vía **SharedArrayBuffer** transferido.

## SharedWorker (`workers/ecos-shared.worker.ts`)

- Sincroniza filtro enfermedad/horizonte entre pestañas abiertas en `/alertas`.
- Patrón fan-out local: un mensaje → todos los `MessagePort` conectados.

## Service Worker (`public/sw.js`)

- Producción: caché del shell (`/`, `/alertas`, `/pronostico`); **API y `/ws` siempre red**.

## WebSocket (`GET` upgrade → `/ws/alerts`)

- Cada ~25 s envía resumen (`total`, críticas, altas); el front hace `mutate()` de SWR si cambia.

## crossOriginIsolated

- No activamos COOP/COEP por defecto: rompe tiles MapLibre y CDN externos.
- SAB es opcional; sin aislamiento el worker usa solo `postMessage`.

## gRPC / contract-first

- Contrato OpenAPI existente en FastAPI (`/docs`).
- gRPC binario queda para un servicio interno futuro (p. ej. batch de pronóstico); el navegador sigue en REST + WS.
