"use client"

/** SharedWorker + postMessage entre pestañas para filtros de alertas. */

type Handler = (disease: string, horizon: number) => void

let shared: SharedWorker | null = null
const tabId = typeof crypto !== "undefined" ? crypto.randomUUID() : String(Date.now())

export function bindSharedAlertFilters(onRemoteChange: Handler): () => void {
  if (typeof SharedWorker === "undefined") return () => {}

  if (!shared) {
    try {
      shared = new SharedWorker(new URL("../../workers/ecos-shared.worker.ts", import.meta.url), {
        type: "module",
        name: "ecos-alert-filters",
      })
    } catch {
      return () => {}
    }
  }

  const port = shared.port
  const listener = (ev: MessageEvent<{ type: string; disease: string; horizon: number; sourceId: string }>) => {
    const data = ev.data
    if (data?.type !== "filter-sync" || data.sourceId === tabId) return
    onRemoteChange(data.disease, data.horizon)
  }
  port.addEventListener("message", listener)
  port.start()

  return () => port.removeEventListener("message", listener)
}

export function publishAlertFilters(disease: string, horizon: number) {
  if (!shared) return
  shared.port.postMessage({
    type: "filter-sync",
    disease,
    horizon,
    sourceId: tabId,
  })
}
