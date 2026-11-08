/// <reference lib="webworker" />

/** SharedWorker: sincroniza filtros de /alertas entre pestañas (fan-out en el cliente). */

type FilterSync = {
  type: "filter-sync"
  disease: string
  horizon: number
  sourceId: string
}

declare const self: SharedWorkerGlobalScope

const ports: MessagePort[] = []

self.onconnect = (event: MessageEvent) => {
  const port = event.ports[0]
  ports.push(port)

  port.onmessage = (ev: MessageEvent<FilterSync>) => {
    const data = ev.data
    if (data?.type !== "filter-sync") return
    for (const p of ports) {
      if (p === port) continue
      p.postMessage(data)
    }
  }

  port.start()
}
