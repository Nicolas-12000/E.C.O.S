"use client"

import { useMemo, useState } from "react"
import useSWR from "swr"
import { Badge } from "@/components/ui/Badge"
import { LottieLoader } from "@/components/ui/LottieLoader"
import { fetcher } from "@/lib/api"

interface AlertItem {
  municipio_code: string
  municipio_name?: string | null
  departamento_code: string
  disease: string
  epi_year: number
  epi_week: number
  cases_total?: number | null
  predicted_cases?: number | null
  horizon_weeks?: number | null
  outbreak_threshold?: number | null
  risk_level: "critical" | "high" | "moderate" | "low"
  signals?: {
    trends_score: number
    rss_mentions: number
    signals_score: number
  } | null
}

interface AlertsResponse {
  mode?: "forecast" | "historic" | "unavailable"
  is_stale?: boolean
  title?: string
  as_of_week_start_date?: string
  as_of_epi_year?: number
  as_of_epi_week?: number
  model_name?: string
  horizon_weeks?: number
  alerts: AlertItem[]
  total: number
  latest_week?: string
  outbreak_threshold?: number | null
  disease_filter?: string
  message?: string
}

const DISEASES = [
  { value: "", label: "Todas" },
  { value: "dengue", label: "Dengue" },
  { value: "malaria", label: "Malaria" },
  { value: "zika", label: "Zika" },
  { value: "chikungunya", label: "Chikungunya" },
]

const riskClasses: Record<string, string> = {
  critical: "bg-(--color-danger-alpha) text-(--color-danger)",
  high: "bg-(--color-warning-alpha) text-(--color-warning)",
  moderate: "bg-(--color-tertiary-alpha) text-(--color-tertiary)",
  low: "bg-(--color-surface) text-(--color-muted)",
}

export default function AlertasPage() {
  const [disease, setDisease] = useState("")
  const [horizon, setHorizon] = useState(1)
  const { data, error, isLoading } = useSWR<AlertsResponse>(
    `/api/v3/alerts?${disease ? `disease=${disease}&` : ""}horizon_weeks=${horizon}&limit=50`,
    fetcher,
  )

  const alerts = useMemo(() => data?.alerts ?? [], [data])
  const isForecast = data?.mode === "forecast"
  const headerBadge = data?.is_stale ? "Corte antiguo" : isForecast ? "Pronóstico" : "Histórico"

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-10 max-w-6xl min-h-screen">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
        <div>
          <Badge variant="outline" className="mb-3">{headerBadge}</Badge>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-(--color-primary)">
            {data?.title ?? "Municipios en vigilancia"}
          </h1>
          <p className="text-(--color-secondary) mt-2 max-w-2xl">
            {isForecast
              ? "Prioriza municipios donde el modelo espera superar el umbral endémico en el horizonte elegido."
              : "Muestra el último corte observado en el archivo cuando no hay corrida de pronóstico guardada."}
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-xs uppercase tracking-[0.2em] text-(--color-muted) font-semibold">Enfermedad</label>
            <select
              value={disease}
              onChange={(e) => setDisease(e.target.value)}
              className="bg-(--color-background) border border-(--color-border) rounded-md px-3 py-2 text-sm text-(--color-primary)"
            >
              {DISEASES.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          {isForecast && (
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-[0.2em] text-(--color-muted) font-semibold">Horizonte</label>
              <select
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
                className="bg-(--color-background) border border-(--color-border) rounded-md px-3 py-2 text-sm text-(--color-primary)"
              >
                {[1, 2, 3, 4].map((h) => (
                  <option key={h} value={h}>
                    +{h} semana{h > 1 ? "s" : ""}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-(--color-surface) border border-(--color-border) rounded-md p-4">
          <p className="text-[10px] uppercase tracking-wider text-(--color-muted) font-semibold">Total</p>
          <p className="text-2xl font-bold text-(--color-primary) mt-2">{data?.total ?? 0}</p>
          <p className="text-xs text-(--color-muted) mt-1">{data?.mode ?? "—"}</p>
        </div>
        <div className="bg-(--color-surface) border border-(--color-border) rounded-md p-4">
          <p className="text-[10px] uppercase tracking-wider text-(--color-muted) font-semibold">Casos observados hasta</p>
          <p className="text-sm font-bold text-(--color-primary) mt-2">
            {data?.as_of_week_start_date ?? data?.latest_week ?? "Sin datos"}
          </p>
          {data?.as_of_epi_week != null && (
            <p className="text-xs text-(--color-muted) mt-1">S{data.as_of_epi_week} {data.as_of_epi_year}</p>
          )}
        </div>
        <div className="bg-(--color-surface) border border-(--color-border) rounded-md p-4">
          <p className="text-[10px] uppercase tracking-wider text-(--color-muted) font-semibold">Modelo</p>
          <p className="text-sm font-bold text-(--color-primary) mt-2">{data?.model_name ?? "—"}</p>
          <p className="text-xs text-(--color-muted) mt-1">
            {isForecast ? `Horizonte +${horizon} sem` : "Sin corrida semanal"}
          </p>
        </div>
      </div>

      <div className="bg-(--color-surface) border border-(--color-border) rounded-md p-4">
        {isLoading ? (
          <div className="min-h-55 flex items-center justify-center">
            <LottieLoader variant="loading" message="Cargando alertas..." />
          </div>
        ) : error ? (
          <div className="min-h-50 flex flex-col items-center justify-center gap-2 text-sm text-(--color-secondary)">
            <Badge variant="outline">Sin conexion</Badge>
            <p>No se pudieron cargar las alertas.</p>
          </div>
        ) : alerts.length === 0 ? (
          <div className="min-h-50 flex flex-col items-center justify-center gap-2 text-sm text-(--color-secondary)">
            <Badge variant="outline">Sin datos</Badge>
            <p>
              {isForecast
                ? "No hay municipios por encima del umbral en este horizonte. Ejecuta el job semanal si aún no hay corrida."
                : "No hay alertas para el filtro actual."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {alerts.map((alert) => (
              <div
                key={`${alert.municipio_code}-${alert.disease}-${alert.epi_week}`}
                className="border border-(--color-border) rounded-md p-4 bg-(--color-background)"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-(--color-primary)">
                      {alert.municipio_name ?? alert.municipio_code}
                    </p>
                    <p className="text-xs text-(--color-muted)">
                      Dpto {alert.departamento_code} · objetivo S{alert.epi_week} {alert.epi_year}
                    </p>
                  </div>
                  <span
                    className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-sm ${riskClasses[alert.risk_level] || riskClasses.moderate}`}
                  >
                    {alert.risk_level}
                  </span>
                </div>
                <p className="text-sm text-(--color-secondary) mt-3 capitalize">{alert.disease}</p>
                <p className="text-xl font-bold text-(--color-primary)">
                  {isForecast && alert.predicted_cases != null
                    ? `${alert.predicted_cases} casos esp.`
                    : `${alert.cases_total ?? 0} casos`}
                </p>
                {alert.signals && (
                  <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-(--color-muted)">
                    <div>
                      <p className="uppercase tracking-wider text-[9px]">RSS</p>
                      <p>{alert.signals.rss_mentions}</p>
                    </div>
                    <div>
                      <p className="uppercase tracking-wider text-[9px]">Score</p>
                      <p>{alert.signals.signals_score}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
