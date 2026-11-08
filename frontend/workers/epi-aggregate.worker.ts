/// <reference lib="webworker" />

/** Web Worker: agregación pesada fuera del main thread (mejor INP). */

export type AlertWire = {
  departamento_code: string
  disease: string
  risk_level: string
  predicted_cases?: number | null
  cases_total?: number | null
}

export type AggregateResult = {
  id: string
  byDisease: { disease: string; count: number; load: number }[]
  byDept: { code: string; count: number }[]
  critical: number
  high: number
  transport: "postMessage" | "sharedArrayBuffer"
  ms: number
}

type AggregateMsg = {
  type: "aggregate"
  id: string
  alerts: AlertWire[]
  sharedBuffer?: SharedArrayBuffer
}

function sumCases(rows: AlertWire[]): number[] {
  return rows.map((r) => {
    const v = r.predicted_cases ?? r.cases_total ?? 0
    return Number.isFinite(v) ? Number(v) : 0
  })
}

function aggregatePostMessage(alerts: AlertWire[]): Omit<AggregateResult, "id" | "transport" | "ms"> {
  const byDisease = new Map<string, { count: number; load: number }>()
  const byDept = new Map<string, number>()
  let critical = 0
  let high = 0

  for (const a of alerts) {
    if (a.risk_level === "critical") critical += 1
    if (a.risk_level === "high") high += 1
    const load = a.predicted_cases ?? a.cases_total ?? 0
    const d = byDisease.get(a.disease) ?? { count: 0, load: 0 }
    d.count += 1
    d.load += Number(load) || 0
    byDisease.set(a.disease, d)
    byDept.set(a.departamento_code, (byDept.get(a.departamento_code) ?? 0) + 1)
  }

  return {
    byDisease: [...byDisease.entries()]
      .map(([disease, v]) => ({ disease, count: v.count, load: Math.round(v.load) }))
      .sort((a, b) => b.load - a.load),
    byDept: [...byDept.entries()]
      .map(([code, count]) => ({ code, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8),
    critical,
    high,
  }
}

function aggregateWithSab(values: Float64Array): number {
  let total = 0
  for (let i = 0; i < values.length; i += 1) total += values[i]
  return total
}

self.onmessage = (ev: MessageEvent<AggregateMsg>) => {
  const msg = ev.data
  if (msg?.type !== "aggregate") return

  const t0 = performance.now()
  let transport: AggregateResult["transport"] = "postMessage"

  if (msg.sharedBuffer && typeof SharedArrayBuffer !== "undefined") {
    transport = "sharedArrayBuffer"
    const view = new Float64Array(msg.sharedBuffer)
    aggregateWithSab(view)
  }

  const core = aggregatePostMessage(msg.alerts)
  const result: AggregateResult = {
    id: msg.id,
    ...core,
    transport,
    ms: Math.round(performance.now() - t0),
  }
  self.postMessage(result)
}
