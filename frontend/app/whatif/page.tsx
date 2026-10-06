"use client"

import { useState } from "react"
import useSWR from "swr"
import { Badge } from "@/components/ui/Badge"
import { LottieLoader } from "@/components/ui/LottieLoader"
import { fetcher, poster } from "@/lib/api"
import { FlaskConical } from "lucide-react"

const MUNICIPIOS = [
  { code: "86865", name: "Puerto Asís" },
  { code: "05500", name: "Medellín" },
  { code: "52001", name: "Pasto" },
]

const DISEASES = ["dengue", "malaria", "zika", "chikungunya"]

const ADJUSTMENT_KEYS = [
  { key: "vaccination_coverage_pct", label: "Cobertura vacunal (Δ %)", min: -20, max: 30, step: 1 },
  { key: "mobility_index", label: "Índice movilidad (Δ)", min: -0.5, max: 0.5, step: 0.05 },
  { key: "precipitation_mm", label: "Precipitación (Δ mm)", min: -50, max: 100, step: 5 },
]

interface WhatIfResponse {
  original_predictions: { predicted_cases: number }[]
  adjusted_predictions: { predicted_cases: number }[]
  delta_total: number
  scenario_id?: string | null
}

interface ScenarioRow {
  scenario_id: string
  created_at: string
  municipio_code: string
  disease: string
  weeks_ahead: number
  delta_total: number | null
  notes?: string | null
}

export default function WhatIfPage() {
  const [municipio, setMunicipio] = useState(MUNICIPIOS[0].code)
  const [disease, setDisease] = useState("dengue")
  const [weeksAhead, setWeeksAhead] = useState(4)
  const [adjustments, setAdjustments] = useState<Record<string, number>>({})
  const [saveScenario, setSaveScenario] = useState(false)
  const [notes, setNotes] = useState("")
  const [result, setResult] = useState<WhatIfResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  const { data: saved, mutate } = useSWR<{ scenarios: ScenarioRow[] }>(
    "/api/v3/whatif/scenarios?limit=10",
    fetcher,
  )

  const runSimulation = async () => {
    setRunning(true)
    setRunError(null)
    try {
      const payload: Record<string, unknown> = {
        municipio_code: municipio,
        disease,
        weeks_ahead: weeksAhead,
        adjustments: Object.fromEntries(
          Object.entries(adjustments).filter(([, v]) => v !== 0),
        ),
        save_scenario: saveScenario,
      }
      if (notes.trim()) payload.notes = notes.trim()
      const res = await poster("/api/v3/whatif", payload)
      setResult(res as WhatIfResponse)
      if (saveScenario) mutate()
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Error en simulación")
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-10 max-w-4xl min-h-screen">
      <Badge variant="outline" className="mb-3 w-fit">
        <FlaskConical className="w-3 h-3 mr-1 inline" />
        What-if
      </Badge>
      <h1 className="text-3xl font-bold text-(--color-primary) mb-2">Simulación de escenarios</h1>
      <p className="text-(--color-secondary) mb-8">
        Ajusta variables exógenas y compara el total pronosticado vs. la línea base del modelo servido.
      </p>

      <div className="space-y-6 rounded-lg border border-(--color-border) bg-(--color-surface) p-6 mb-8">
        <div className="grid sm:grid-cols-3 gap-4">
          <label className="text-sm flex flex-col gap-1">
            <span className="text-(--color-muted)">Municipio</span>
            <select
              className="rounded-md border border-(--color-border) px-3 py-2 bg-(--color-background)"
              value={municipio}
              onChange={(e) => setMunicipio(e.target.value)}
            >
              {MUNICIPIOS.map((m) => (
                <option key={m.code} value={m.code}>{m.name}</option>
              ))}
            </select>
          </label>
          <label className="text-sm flex flex-col gap-1">
            <span className="text-(--color-muted)">Enfermedad</span>
            <select
              className="rounded-md border border-(--color-border) px-3 py-2 bg-(--color-background)"
              value={disease}
              onChange={(e) => setDisease(e.target.value)}
            >
              {DISEASES.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>
          <label className="text-sm flex flex-col gap-1">
            <span className="text-(--color-muted)">Horizonte (semanas)</span>
            <select
              className="rounded-md border border-(--color-border) px-3 py-2 bg-(--color-background)"
              value={weeksAhead}
              onChange={(e) => setWeeksAhead(Number(e.target.value))}
            >
              {[1, 2, 3, 4].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
        </div>

        {ADJUSTMENT_KEYS.map(({ key, label, min, max, step }) => (
          <label key={key} className="block text-sm">
            <span className="text-(--color-muted)">{label}</span>
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={adjustments[key] ?? 0}
              onChange={(e) =>
                setAdjustments((prev) => ({ ...prev, [key]: Number(e.target.value) }))
              }
              className="w-full mt-1"
            />
            <span className="font-mono text-xs">{adjustments[key] ?? 0}</span>
          </label>
        ))}

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={saveScenario}
            onChange={(e) => setSaveScenario(e.target.checked)}
          />
          Guardar escenario en Supabase (requiere migración 0005)
        </label>
        {saveScenario && (
          <input
            type="text"
            placeholder="Notas opcionales"
            className="w-full rounded-md border border-(--color-border) px-3 py-2 text-sm"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        )}

        <button
          type="button"
          onClick={runSimulation}
          disabled={running}
          className="px-4 py-2 rounded-md bg-(--color-tertiary) text-white font-semibold disabled:opacity-50"
        >
          {running ? "Calculando…" : "Ejecutar simulación"}
        </button>
        {runError && <p className="text-(--color-danger) text-sm">{runError}</p>}
      </div>

      {running && <LottieLoader />}

      {result && (
        <div className="rounded-lg border border-(--color-border) p-6 mb-8">
          <p className="text-lg">
            Δ total ({weeksAhead} sem.):{" "}
            <strong className={result.delta_total < 0 ? "text-(--color-success)" : "text-(--color-warning)"}>
              {result.delta_total > 0 ? "+" : ""}{result.delta_total}
            </strong>{" "}
            casos acumulados
          </p>
          {result.scenario_id && (
            <p className="text-xs text-(--color-muted) mt-2">Guardado: {result.scenario_id}</p>
          )}
        </div>
      )}

      {saved?.scenarios?.length ? (
        <div>
          <h2 className="font-semibold mb-3">Escenarios recientes</h2>
          <ul className="space-y-2 text-sm">
            {saved.scenarios.map((s) => (
              <li
                key={s.scenario_id}
                className="flex justify-between border-b border-(--color-border)/50 py-2"
              >
                <span>
                  {s.municipio_code} · {s.disease} · {s.weeks_ahead} sem.
                </span>
                <span className="font-mono">{s.delta_total ?? "—"}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
