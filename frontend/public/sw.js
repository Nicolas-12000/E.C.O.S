/* ECOS service worker — shell offline; API siempre network-first. */
const SHELL = "ecos-shell-v1"
const SHELL_URLS = ["/", "/alertas", "/pronostico"]

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL).then((cache) => cache.addAll(SHELL_URLS).catch(() => undefined)),
  )
  self.skipWaiting()
})

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url)
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/ws")) {
    return
  }
  if (event.request.method !== "GET") return

  event.respondWith(
    caches.open(SHELL).then(async (cache) => {
      const cached = await cache.match(event.request)
      if (cached) return cached
      try {
        const fresh = await fetch(event.request)
        if (fresh.ok && url.origin === self.location.origin) {
          cache.put(event.request, fresh.clone())
        }
        return fresh
      } catch {
        return (
          (await cache.match("/")) ||
          new Response("Sin conexión", { status: 503, headers: { "Content-Type": "text/plain" } })
        )
      }
    }),
  )
})
