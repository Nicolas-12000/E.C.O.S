"use client"

import { useMemo, useState } from "react"
import useSWR from "swr"
import { Badge } from "@/components/ui/Badge"
import { LottieLoader } from "@/components/ui/LottieLoader"
import { fetcher } from "@/lib/api"
import { LineChart } from "lucide-react"

const MUNICIPIOS = [
  { code: "86865", name: "Puerto Asís" },
  { code: "05500", name: "Medellín" },
  { code: "52001", name: "Pasto" },
  { code: "76760", name: "Santiago de Cali" },
  { code: "11001", name: "Bogotá D.C." },
]

const DISEASES = ["dengue", "malaria", "zika", "chikungunya"]

interface HistoryItem {
  epi_year: number
  epi_week: number
  week_start_date: string
  cases_total: number
}

interface PredictionItem {
  epi_year: number
  epi_week: number
  week_start_date: string
  predicted_cases: number
  outbreak_flag: boolean
}

interface TimeseriesResponse {
  municipio_code: string
  disease: string
  history: HistoryItem[]
  predictions: PredictionItem[]
  served_model?: string
}

function SeriesChart({
  history,
  predictions,
}: {
  history: HistoryItem[]
  predictions: PredictionItem[]
}) {
  const hist = history.slice(-26)
  const histVals = hist.map((h) => h.cases_total)
  const predVals = predictions.map((p) => p.predicted_cases)
  const all = [...histVals, ...predVals]
  const width = 640
  const height = 200
  const pad = 24
  const maxV = Math.max(...all, 1)
  const histCount = histVals.length
  const total = histCount + predVals.length
  const step = total > 1 ? (width - pad * 2) / (total - 1) : 0

  const point = (i: number, v: number) => {
    const x = pad + step * i
    const y = height - pad - (v / maxV) * (height - pad * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }

  const histPath =
    histVals.length > 0
      ? histVals.map((v, i) => `${i === 0 ? "M" : "L"} ${point(i, v).replace(",", " ")}`).join(" ")
      : ""

  const predPath =
    predVals.length > 0
      ? predVals
          .map((v, i) => {
            const idx = histCount + i
            const [x, y] = point(idx, v).split(",")
            return `${i === 0 ? "M" : "L"} ${x} ${y}`
          })
          .join(" ")
      : ""

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-48 text-(--color-tertiary)">
      <line
        x1={pad + step * (histCount - 1)}
        y1={pad}
        x2={pad + step * (histCount - 1)}
        y2={height - pad}
        className="stroke-(--color-border)"
        strokeDasharray="4 4"
      />
      {histPath && <path d={histPath} fill="none" stroke="currentColor" strokeWidth="2" />}
      {predPath && (
        <path
          d={predPath}
          fill="none"
          stroke="var(--color-warning)"
          strokeWidth="2"
          strokeDasharray="6 4"
        />
      )}
    </svg>
  )
}

export default function PronosticoPage() {
  const [municipio, setMunicipio] = useState(MUNICIPIOS[0].code)
  const [disease, setDisease] = useState("dengue")
  const [weeksHistory, setWeeksHistory] = useState(52)
  const [weeksAhead, setWeeksAhead] = useState(4)

  const url = `/api/v3/timeseries?municipio_code=${municipio}&disease=${disease}&weeks_history=${weeksHistory}&weeks_ahead=${weeksAhead}`
  const { data, error, isLoading } = useSWR<TimeseriesResponse>(url, fetcher)

  const lastObserved = useMemo(() => {
    if (!data?.history?.length) return null
    return data.history[data.history.length - 1]
  }, [data])

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-10 max-w-5xl min-h-screen">
      <div className="flex flex-col gap-2 mb-8">
        <Badge variant="outline" className="w-fit">
          <LineChart className="w-3 h-3 mr-1 inline" />
          Serie + pronóstico
        </Badge>
        <h1 className="text-3xl font-bold text-(--color-primary)">Pronóstico municipal</h1>
        <p className="text-(--color-secondary) max-w-2xl">
          Historia observada y horizonte modelado para un municipio. Línea punteada = semanas proyectadas.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-(--color-muted)">Municipio</span>
          <select
            className="rounded-md border border-(--color-border) bg-(--color-surface) px-3 py-2"
            value={municipio}
            onChange={(e) => setMunicipio(e.target.value)}
          >
            {MUNICIPIOS.map((m) => (
              <option key={m.code} value={m.code}>
                {m.name} ({m.code})
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-(--color-muted)">Enfermedad</span>
          <select
            className="rounded-md border border-(--color-border) bg-(--color-surface) px-3 py-2"
            value={disease}
            onChange={(e) => setDisease(e.target.value)}
          >
            {DISEASES.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-(--color-muted)">Semanas historia</span>
          <select
            className="rounded-md border border-(--color-border) bg-(--color-surface) px-3 py-2"
            value={weeksHistory}
            onChange={(e) => setWeeksHistory(Number(e.target.value))}
          >
            {[26, 52, 104].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-(--color-muted)">Horizonte</span>
          <select
            className="rounded-md border border-(--color-border) bg-(--color-surface) px-3 py-2"
            value={weeksAhead}
            onChange={(e) => setWeeksAhead(Number(e.target.value))}
          >
            {[1, 2, 3, 4].map((n) => (
              <option key={n} value={n}>{n} semana{n > 1 ? "s" : ""}</option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && <LottieLoader />}
      {error && (
        <p className="text-(--color-danger)">No se pudo cargar la serie. ¿Backend activo en {process.env.NEXT_PUBLIC_API_URL || "127.0.0.1:8000"}?</p>
      )}

      {data && (
        <div className="rounded-lg border border-(--color-border) bg-(--color-surface) p-6 space-y-6">
          <div className="flex flex-wrap items-center gap-3 text-sm text-(--color-secondary)">
            {data.served_model && (
              <Badge variant="secondary">Modelo servido: {data.served_model}</Badge>
            )}
            {lastObserved && (
              <span>
                Último corte: {lastObserved.week_start_date} (S{lastObserved.epi_week} / {lastObserved.epi_year}) —{" "}
                {lastObserved.cases_total} casos
              </span>
            )}
          </div>
          <SeriesChart history={data.history} predictions={data.predictions} />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-(--color-muted) border-b border-(--color-border)">
                  <th className="py-2 pr-4">Semana</th>
                  <th className="py-2 pr-4">Inicio</th>
                  <th className="py-2 pr-4">Observado</th>
                  <th className="py-2">Pronóstico</th>
                </tr>
              </thead>
              <tbody>
                {data.predictions.map((p) => (
                  <tr key={`${p.epi_year}-${p.epi_week}`} className="border-b border-(--color-border)/50">
                    <td className="py-2 pr-4">{p.epi_week}/{p.epi_year}</td>
                    <td className="py-2 pr-4">{p.week_start_date}</td>
                    <td className="py-2 pr-4 text-(--color-muted)">—</td>
                    <td className="py-2 font-mono">
                      {p.predicted_cases.toFixed(1)}
                      {p.outbreak_flag ? " ⚠" : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
