/** En Vercel: rutas `/api/*` vía rewrites (mismo origen, sin CORS). Local: backend directo. */
const ENV_API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? ""

export function resolveApiBase(): string {
  if (typeof window === "undefined") {
    return ENV_API || "http://127.0.0.1:8000"
  }
  const host = window.location.hostname
  if (host === "localhost" || host === "127.0.0.1") {
    return ENV_API || "http://127.0.0.1:8000"
  }
  // Producción / preview Vercel: proxy Next → Render
  if (ENV_API) return ""
  return "http://127.0.0.1:8000"
}

/** Preferir `resolveApiBase()` en cliente; estático puede variar SSR vs hidratación. */
export const API_BASE = resolveApiBase()

interface FetchError extends Error {
  info?: unknown
  status?: number
}

export const fetcher = async (url: string) => {
  const base = resolveApiBase()
  const fullUrl = url.startsWith("http") ? url : `${base}${url}`
  const res = await fetch(fullUrl)

  if (!res.ok) {
    const error: FetchError = new Error("An error occurred while fetching the data.")
    const info = await res.json().catch(() => ({}))
    error.info = info
    error.status = res.status
    throw error
  }

  return res.json()
}

export const poster = async (url: string, body?: Record<string, unknown> | unknown) => {
  const base = resolveApiBase()
  const fullUrl = url.startsWith("http") ? url : `${base}${url}`
  const res = await fetch(fullUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    const error: FetchError = new Error("An error occurred while posting data.")
    const info = await res.json().catch(() => ({}))
    error.info = info
    error.status = res.status
    throw error
  }

  return res.json()
}
