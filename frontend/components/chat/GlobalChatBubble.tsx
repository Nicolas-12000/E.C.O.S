"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Bot, Loader2, MessageCircle, ChevronDown, Trash2, Sparkles, LogIn, KeyRound } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { API_BASE } from "@/lib/api"

interface ChatSource { title: string; excerpt: string; source_type: "doc" | "data" }
interface ChatMessage { role: "user" | "assistant"; content: string; sources?: ChatSource[] }

const QUICK_ACTIONS = [
  "¿Riesgo de dengue en Nariño?",
  "Brotes en el Pacífico",
  "Malaria 2022 vs 2020",
  "¿Movilidad y riesgo?",
]

const CAPABILITIES = [
  { emoji: "📊", text: "Consultar riesgo por departamento" },
  { emoji: "📰", text: "Noticias epidemiológicas recientes" },
  { emoji: "🔍", text: "Tendencias de búsqueda" },
  { emoji: "🧠", text: "Explicar predicciones (SHAP)" },
  { emoji: "🌡️", text: "Datos climáticos" },
]

const WELCOME: ChatMessage = {
  role: "assistant",
  content: "👋 ¡Hola! Soy el asistente de **ECOS** — tu copiloto de vigilancia epidemiológica.\n\nPregúntame sobre dengue, malaria, zika o chikungunya en cualquier departamento.",
}

const CHAT_TOKEN_KEY = "ecos_chat_token"
/** Seed 0007 — Bayern 4-3 Madrid, Allianz, abril 2026 */
const DEMO_EMAIL = "camavinga@allianz2026.ecos"
const DEMO_PASSWORD = "Bayern4-3"

export function GlobalChatBubble() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [chatToken, setChatToken] = useState<string | null>(null)
  const [loginEmail, setLoginEmail] = useState("")
  const [loginPassword, setLoginPassword] = useState("")
  const [loginError, setLoginError] = useState("")
  const [loginLoading, setLoginLoading] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    try {
      setChatToken(localStorage.getItem(CHAT_TOKEN_KEY))
    } catch {
      setChatToken(null)
    }
  }, [])

  useEffect(() => {
    if (isOpen && chatToken) endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isOpen, chatToken])

  const authHeaders = (extra?: Record<string, string>) => {
    const headers: Record<string, string> = { "Content-Type": "application/json", ...extra }
    if (chatToken) headers.Authorization = `Bearer ${chatToken}`
    return headers
  }

  const clearAuth = () => {
    try {
      localStorage.removeItem(CHAT_TOKEN_KEY)
    } catch {
      /* ignore */
    }
    setChatToken(null)
    setMessages([WELCOME])
    setSessionId(null)
  }

  const fillDemoCredentials = () => {
    setLoginEmail(DEMO_EMAIL)
    setLoginPassword(DEMO_PASSWORD)
    setLoginError("")
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (loginLoading) return
    setLoginError("")
    setLoginLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/demo-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login: loginEmail.trim(), password: loginPassword }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || "No se pudo iniciar sesión")
      localStorage.setItem(CHAT_TOKEN_KEY, data.access_token)
      setChatToken(data.access_token)
      setLoginEmail("")
      setLoginPassword("")
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "Error de acceso")
    } finally {
      setLoginLoading(false)
    }
  }

  const sendMessage = async (text: string) => {
    if (!chatToken || !text.trim() || isLoading) return
    const msg = text.trim()
    setInput("")
    setMessages(p => [...p, { role: "user", content: msg }])
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ question: msg, session_id: sessionId }),
      })
      const data = await res.json()
      if (res.status === 401) {
        clearAuth()
        throw new Error("Sesión expirada")
      }
      if (!res.ok) throw new Error(data.detail || "Error")
      setSessionId(data.session_id)
      setMessages(p => [...p, { role: "assistant", content: data.answer, sources: data.sources }])
    } catch {
      setMessages(p => [...p, { role: "assistant", content: "⚠️ No pudimos conectarnos en este momento. Intenta de nuevo en unos minutos." }])
    } finally {
      setIsLoading(false)
    }
  }

  const clearChat = async () => {
    try {
      if (sessionId) {
        await fetch(`${API_BASE}/api/v1/chat/clear`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ session_id: sessionId }),
        })
      }
    } catch {
      /* ignore */
    } finally {
      setMessages([WELCOME])
      setSessionId(null)
    }
  }

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); sendMessage(input) }

  const renderContent = (text: string) => {
    return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**"))
        return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
      return part.split("\n").map((line, j) => (
        <span key={`${i}-${j}`}>{j > 0 && <br />}{line}</span>
      ))
    })
  }

  return (
    <>
      {/* ── FAB Button ── */}
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 z-9999 group transition-all duration-300 ${isOpen ? "scale-0 opacity-0 pointer-events-none" : "scale-100 opacity-100"}`}
        aria-label="Abrir asistente ECOS"
      >
        <span className="absolute inset-0 rounded-full bg-[#B8422E] animate-ping opacity-20" />
        <span className="relative flex items-center justify-center w-14 h-14 bg-[#B8422E] text-white rounded-full shadow-lg hover:bg-tertiary-hover hover:shadow-xl hover:scale-105 transition-all">
          <MessageCircle className="w-6 h-6" />
        </span>
      </button>

      {/* ── Chat Window ── */}
      <div
        className={`fixed bottom-6 right-6 z-9999 w-100 max-w-[calc(100vw-2rem)] h-140 max-h-[calc(100vh-6rem)] flex flex-col rounded-2xl overflow-hidden transition-all duration-300 origin-bottom-right ${isOpen
            ? "scale-100 opacity-100"
            : "scale-95 opacity-0 pointer-events-none"
          }`}
        style={{
          backgroundColor: "#FFFFFF",
          border: "1px solid #E5E2DC",
          boxShadow: "0 20px 60px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.06)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3 shrink-0"
          style={{ backgroundColor: "#F7F5F2", borderBottom: "1px solid #E5E2DC" }}
        >
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ backgroundColor: "rgba(184,66,46,0.08)" }}>
                <Bot className="w-4 h-4" style={{ color: "#B8422E" }} />
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white" style={{ backgroundColor: "#039855" }} />
            </div>
            <div>
              <span className="font-bold text-sm leading-none block" style={{ color: "#1A1C1E" }}>Asistente ECOS</span>
              <span className="text-[10px] uppercase tracking-wider" style={{ color: "#9CA3AF" }}>RAG · Epidemiología</span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {chatToken && (
              <button
                type="button"
                onClick={clearAuth}
                className="text-[10px] px-2 py-1 rounded-md transition-colors hover:bg-gray-100"
                style={{ color: "#9CA3AF" }}
                title="Cerrar sesión demo"
              >
                Salir
              </button>
            )}
            {chatToken && messages.length > 1 && (
              <button
                onClick={() => clearChat()} 
                className="p-1.5 rounded-md transition-colors hover:bg-red-50" 
                style={{ color: "#9CA3AF" }} 
                aria-label="Limpiar"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
            <button onClick={() => setIsOpen(false)} className="p-1.5 rounded-md transition-colors hover:bg-gray-100" style={{ color: "#6C7278" }}>
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Login demo */}
        {!chatToken ? (
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4" style={{ backgroundColor: "#FFFFFF" }}>
            <div className="text-center pt-2">
              <div
                className="w-12 h-12 mx-auto rounded-full flex items-center justify-center mb-3"
                style={{ backgroundColor: "rgba(184,66,46,0.08)" }}
              >
                <KeyRound className="w-6 h-6" style={{ color: "#B8422E" }} />
              </div>
              <p className="text-sm font-semibold" style={{ color: "#1A1C1E" }}>Acceso al asistente IA</p>
              <p className="text-xs mt-1 px-2" style={{ color: "#9CA3AF" }}>
                Inicia sesión para probar el chat RAG (requisito del proyecto).
              </p>
            </div>

            <button
              type="button"
              onClick={fillDemoCredentials}
              className="text-left rounded-xl p-3 transition-all hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
              style={{
                backgroundColor: "#FFF8F6",
                border: "1px dashed #B8422E",
                boxShadow: "0 0 0 0 rgba(184,66,46,0.15)",
              }}
              title="Clic para rellenar correo y contraseña"
            >
              <p className="text-[10px] uppercase tracking-wider font-semibold mb-2" style={{ color: "#B8422E" }}>
                Demo · clic para autocompletar
              </p>
              <p className="text-[12px]" style={{ color: "#6C7278" }}>
                <span className="font-medium" style={{ color: "#1A1C1E" }}>Correo:</span> {DEMO_EMAIL}
              </p>
              <p className="text-[12px] mt-1" style={{ color: "#6C7278" }}>
                <span className="font-medium" style={{ color: "#1A1C1E" }}>Contraseña:</span> {DEMO_PASSWORD}
              </p>
              <p className="text-[10px] mt-2 italic" style={{ color: "#9CA3AF" }}>
                Pista: vuelta en Baviera, abril 2026 — marcador del partido
              </p>
            </button>

            <form onSubmit={handleLogin} className="space-y-3">
              <input
                type="email"
                autoComplete="username"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="Correo"
                className="w-full rounded-xl px-4 py-2.5 text-sm"
                style={{ backgroundColor: "#F7F5F2", border: "1px solid #E5E2DC", color: "#1A1C1E" }}
              />
              <input
                type="password"
                autoComplete="current-password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="Contraseña"
                className="w-full rounded-xl px-4 py-2.5 text-sm"
                style={{ backgroundColor: "#F7F5F2", border: "1px solid #E5E2DC", color: "#1A1C1E" }}
              />
              {loginError && (
                <p className="text-xs" style={{ color: "#B8422E" }}>{loginError}</p>
              )}
              <Button type="submit" variant="primary" className="w-full gap-2" disabled={loginLoading || !loginEmail || !loginPassword}>
                {loginLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogIn className="w-4 h-4" />}
                Entrar
              </Button>
            </form>
          </div>
        ) : (
        <>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ backgroundColor: "#FFFFFF" }}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-fade-in-up`}>
              <div
                className="max-w-[85%] px-3.5 py-2.5 text-[13.5px] leading-relaxed whitespace-pre-wrap"
                style={
                  msg.role === "user"
                    ? { backgroundColor: "#B8422E", color: "#FFFFFF", borderRadius: "12px 12px 4px 12px" }
                    : { backgroundColor: "#F7F5F2", color: "#1A1C1E", borderRadius: "12px 12px 12px 4px", border: "1px solid #E5E2DC" }
                }
              >
                {renderContent(msg.content)}
              </div>
            </div>
          ))}

          {/* Typing */}
          {isLoading && (
            <div className="flex justify-start animate-fade-in">
              <div className="px-4 py-3 flex items-center gap-2 rounded-xl" style={{ backgroundColor: "#F7F5F2", border: "1px solid #E5E2DC" }}>
                <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color: "#B8422E" }} />
                <span className="text-xs" style={{ color: "#9CA3AF" }}>Analizando datos...</span>
              </div>
            </div>
          )}

          {/* Capabilities (first message only) */}
          {messages.length <= 1 && !isLoading && (
            <div className="animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
              <div className="rounded-xl p-3 mt-1" style={{ backgroundColor: "#F7F5F2", border: "1px solid #E5E2DC" }}>
                <p className="text-[10px] uppercase tracking-wider font-semibold mb-2.5 flex items-center gap-1" style={{ color: "#9CA3AF" }}>
                  <Sparkles className="w-3 h-3" /> Puedo ayudarte con
                </p>
                <ul className="space-y-1.5">
                  {CAPABILITIES.map((c, i) => (
                    <li key={i} className="text-[12px] flex items-start gap-2" style={{ color: "#6C7278" }}>
                      <span>{c.emoji}</span><span>{c.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <div ref={endRef} />
        </div>

        {/* Quick Actions */}
        {messages.length <= 2 && !isLoading && (
          <div className="px-3 pb-2 flex gap-1.5 flex-wrap shrink-0" style={{ backgroundColor: "#FFFFFF" }}>
            {QUICK_ACTIONS.map((a, i) => (
              <button
                key={i}
                onClick={() => sendMessage(a)}
                className="text-[11px] px-2.5 py-1.5 rounded-full transition-all hover:scale-[1.02]"
                style={{ border: "1px solid #E5E2DC", color: "#6C7278", backgroundColor: "#FFFFFF" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "#B8422E"
                  e.currentTarget.style.color = "#B8422E"
                  e.currentTarget.style.backgroundColor = "rgba(184,66,46,0.04)"
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "#E5E2DC"
                  e.currentTarget.style.color = "#6C7278"
                  e.currentTarget.style.backgroundColor = "#FFFFFF"
                }}
              >
                {a}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="p-3 shrink-0" style={{ backgroundColor: "#FFFFFF", borderTop: "1px solid #E5E2DC" }}>
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pregunta sobre epidemiología..."
              disabled={isLoading}
              className="flex-1 rounded-full px-4 py-2.5 text-sm transition-all disabled:opacity-50"
              style={{
                backgroundColor: "#F7F5F2",
                border: "1px solid #E5E2DC",
                color: "#1A1C1E",
                outline: "none",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "#B8422E"; e.currentTarget.style.boxShadow = "0 0 0 2px rgba(184,66,46,0.08)" }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "#E5E2DC"; e.currentTarget.style.boxShadow = "none" }}
            />
            <Button type="submit" size="icon" shape="pill" variant={input.trim() ? "primary" : "default"} disabled={!input.trim() || isLoading} className="shrink-0">
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
        </>
        )}
      </div>
    </>
  )
}
