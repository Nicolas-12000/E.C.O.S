"use client"

import { useEffect, useRef, useState } from "react"
import { API_BASE } from "@/lib/api"
import { parseAlertsTick, type AlertsTick } from "@/lib/validators/alertsTick"

export type { AlertsTick }

function wsBase(): string {
  if (typeof window === "undefined") return ""
  const base = API_BASE.replace(/\/$/, "")
  if (base.startsWith("http")) {
    return base.replace(/^http/, "ws")
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:"
  return `${proto}//${window.location.host}`
}

export function useAlertsSocket(
  disease: string,
  horizon: number,
  onTick?: (tick: AlertsTick) => void,
) {
  const [tick, setTick] = useState<AlertsTick | null>(null)
  const [connected, setConnected] = useState(false)
  const cb = useRef(onTick)
  cb.current = onTick

  useEffect(() => {
    const params = new URLSearchParams()
    if (disease) params.set("disease", disease)
    params.set("horizon_weeks", String(horizon))
    const url = `${wsBase()}/ws/alerts?${params}`

    let ws: WebSocket | null = null
    let closed = false
    let retry: ReturnType<typeof setTimeout> | null = null

    const connect = () => {
      if (closed) return
      ws = new WebSocket(url)
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!closed) retry = setTimeout(connect, 4000)
      }
      ws.onmessage = (ev) => {
        try {
          const payload = parseAlertsTick(JSON.parse(ev.data))
          if (!payload) return
          setTick(payload)
          cb.current?.(payload)
        } catch {
          /* ignore malformed */
        }
      }
    }

    connect()
    return () => {
      closed = true
      if (retry) clearTimeout(retry)
      ws?.close()
    }
  }, [disease, horizon])

  return { tick, connected }
}
