import type { AggregateResult, AlertWire } from "@/workers/epi-aggregate.worker"

let worker: Worker | null = null
let seq = 0

function getWorker(): Worker | null {
  if (typeof window === "undefined" || typeof Worker === "undefined") return null
  if (!worker) {
    worker = new Worker(new URL("../../workers/epi-aggregate.worker.ts", import.meta.url), {
      type: "module",
    })
  }
  return worker
}

function valuesBuffer(alerts: AlertWire[]): SharedArrayBuffer | undefined {
  if (typeof SharedArrayBuffer === "undefined" || !window.crossOriginIsolated) return undefined
  const buf = new SharedArrayBuffer(Float64Array.BYTES_PER_ELEMENT * Math.max(alerts.length, 1))
  const view = new Float64Array(buf)
  alerts.forEach((a, i) => {
    view[i] = a.predicted_cases ?? a.cases_total ?? 0
  })
  return buf
}

export function aggregateAlertsInWorker(alerts: AlertWire[]): Promise<AggregateResult> {
  const w = getWorker()
  if (!w) {
    return Promise.resolve(fallbackAggregate(alerts))
  }

  const id = `agg-${++seq}`
  return new Promise((resolve, reject) => {
    const onMessage = (ev: MessageEvent<AggregateResult>) => {
      if (ev.data?.id !== id) return
      w.removeEventListener("message", onMessage)
      resolve(ev.data)
    }
    const onError = (err: ErrorEvent) => {
      w.removeEventListener("message", onMessage)
      reject(err.message)
    }
    w.addEventListener("message", onMessage)
    w.addEventListener("error", onError, { once: true })
    const sab = valuesBuffer(alerts)
    w.postMessage(
      {
        type: "aggregate",
        id,
        alerts,
        sharedBuffer: sab,
      },
      sab ? [sab] : [],
    )
  })
}

function fallbackAggregate(alerts: AlertWire[]): AggregateResult {
  const byDisease = new Map<string, { count: number; load: number }>()
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
  }
  return {
    id: "main-thread",
    byDisease: [...byDisease.entries()].map(([disease, v]) => ({
      disease,
      count: v.count,
      load: Math.round(v.load),
    })),
    byDept: [],
    critical,
    high,
    transport: "postMessage",
    ms: 0,
  }
}
