import { API_BASE, authHeaders } from "./api"

// Fetch asosidagi SSE o'quvchi. onData chunk matnini, onError xatolikni beradi.
export interface StreamHandlers {
  onToken?: (text: string) => void
  onEvent?: (event: Record<string, unknown>) => void
  onDone?: () => void
  onError?: (message: string) => void
}

export interface StreamController {
  cancel: () => void
}

/**
 * SSE (text/event-stream) so'rovini yuboradi va "data:" qatorlarini parse qiladi.
 * Chat endpointi "token" event yuboradi; agent endpointi turli event turlarini.
 */
export function streamPost(
  url: string,
  body: unknown,
  handlers: StreamHandlers,
): StreamController {
  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await fetch(API_BASE + url, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!res.ok || !res.body) {
        handlers.onError?.(`HTTP ${res.status}`)
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split("\n\n")
        buffer = parts.pop() ?? ""
        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith("data:")) continue
          const payload = line.slice(5).trim()
          if (payload === "[DONE]") {
            handlers.onDone?.()
            return
          }
          try {
            const evt = JSON.parse(payload) as Record<string, unknown>
            handlers.onEvent?.(evt)
            if (evt.type === "token" && typeof evt.text === "string") {
              handlers.onToken?.(evt.text)
            }
            if (evt.type === "done") {
              handlers.onDone?.()
              return
            }
            if (evt.type === "error") {
              handlers.onError?.(String(evt.message ?? "xatolik"))
              return
            }
          } catch {
            /* qisman JSON — e'tiborsiz qoldiramiz */
          }
        }
      }
      handlers.onDone?.()
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        handlers.onError?.((e as Error).message || "tarmoq xatosi")
      }
    }
  })()

  return { cancel: () => controller.abort() }
}
