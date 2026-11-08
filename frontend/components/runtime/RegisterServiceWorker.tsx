"use client"

import { useEffect, useState } from "react"

/** Service worker: caché del shell; no sustituye al API en vivo. */
export function RegisterServiceWorker() {
  const [isolated, setIsolated] = useState<boolean | null>(null)

  useEffect(() => {
    setIsolated(typeof crossOriginIsolated !== "undefined" ? crossOriginIsolated : false)

    if (process.env.NODE_ENV !== "production") return
    if (!("serviceWorker" in navigator)) return

    const register = async () => {
      try {
        await navigator.serviceWorker.register("/sw.js", { scope: "/" })
      } catch {
        /* SW opcional */
      }
    }
    register()
  }, [])

  if (isolated === null || process.env.NODE_ENV !== "development") return null

  return (
    <span className="sr-only" data-cross-origin-isolated={isolated ? "1" : "0"}>
      {isolated ? "Aislamiento activo (SAB disponible)" : "SAB desactivado (mapas y CDN externos)"}
    </span>
  )
}
