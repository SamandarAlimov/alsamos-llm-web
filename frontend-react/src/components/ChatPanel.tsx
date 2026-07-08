import { useEffect, useRef, useState } from "react"
import type { CSSProperties } from "react"
import { AnimatePresence, motion } from "framer-motion"
import type { ChatMessage, Mode, Skill } from "../types"
import { renderMarkdown } from "../lib/markdown"
import { api } from "../api"

export interface AgentStep {
  id: number
  kind: string
  label: string
}

interface Props {
  mode: Mode
  messages: ChatMessage[]
  steps: AgentStep[]
  streaming: boolean
  skills: Skill[]
  activeSkill: string | null
  onPickSkill: (id: string | null) => void
  onSend: (text: string) => void
  onStop: () => void
  ttsVoice: string
}

const SUGGESTIONS = [
  "React'da drag-and-drop komponent yozib ber",
  "Bozor tahlilini qilib qisqa hisobot tayyorla",
  "Ushbu algoritmni optimallashtir va tushuntir",
  "O'zbek tilida marketing matni yoz",
]

const stepInitial = { opacity: 0, y: 6 }
const stepAnimate = { opacity: 1, y: 0 }
const msgInitial = { opacity: 0, y: 10 }
const msgAnimate = { opacity: 1, y: 0 }
const textareaStyle: CSSProperties = { minHeight: 24 }

function mdObj(text: string) {
  return { __html: renderMarkdown(text) }
}

export default function ChatPanel({
  mode,
  messages,
  steps,
  streaming,
  skills,
  activeSkill,
  onPickSkill,
  onSend,
  onStop,
  ttsVoice,
}: Props) {
  const [text, setText] = useState("")
  const [listening, setListening] = useState(false)
  const taRef = useRef<HTMLTextAreaElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const recogRef = useRef<any>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, steps])

  function grow() {
    const ta = taRef.current
    if (!ta) return
    ta.style.height = "auto"
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px"
  }

  function submit() {
    const t = text.trim()
    if (!t || streaming) return
    onSend(t)
    setText("")
    requestAnimationFrame(() => {
      if (taRef.current) taRef.current.style.height = "auto"
    })
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function toggleMic() {
    const SR: any =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) {
      alert("Brauzeringiz ovozli kiritishni qo'llab-quvvatlamaydi.")
      return
    }
    if (listening) {
      recogRef.current?.stop()
      setListening(false)
      return
    }
    const rec = new SR()
    rec.lang = "uz-UZ"
    rec.interimResults = true
    rec.continuous = false
    rec.onresult = (ev: any) => {
      let s = ""
      for (let i = 0; i < ev.results.length; i++) s += ev.results[i][0].transcript
      setText(s)
    }
    rec.onend = () => setListening(false)
    rec.start()
    recogRef.current = rec
    setListening(true)
  }

  async function speak(t: string) {
    try {
      const r = await api.tts(t.slice(0, 900), ttsVoice)
      const audio = new Audio(r.url)
      audio.play().catch(() => undefined)
    } catch {
      // Fallback: brauzer TTS
      const u = new SpeechSynthesisUtterance(t.slice(0, 900))
      speechSynthesis.speak(u)
    }
  }

  const empty = messages.filter((m) => m.role !== "system").length === 0

  return (
    <>
      <div className="messages">
        {empty && steps.length === 0 ? (
          <div className="hero">
            <div className="logo" style={heroLogoStyle}>
              A
            </div>
            <h1>Alsamos AI bilan boshlang</h1>
            <p>Chuqur fikrlaydigan, o'rganadigan va o'zini tekshiradigan korporativ AI.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion" onClick={() => onSend(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages
              .filter((m) => m.role !== "system")
              .map((m, i) => (
                <motion.div
                  key={i}
                  className="msg"
                  initial={msgInitial}
                  animate={msgAnimate}
                >
                  <div className={`avatar ${m.role === "user" ? "user" : "ai"}`}>
                    {m.role === "user" ? "S" : "A"}
                  </div>
                  <div className="bubble">
                    <div dangerouslySetInnerHTML={mdObj(m.content)} />
                    {m.role === "assistant" && m.content && (
                      <div className="msg-actions">
                        <button className="mini-btn" onClick={() => speak(m.content)}>
                          {"\uD83D\uDD0A Eshitish"}
                        </button>
                        <button
                          className="mini-btn"
                          onClick={() => navigator.clipboard.writeText(m.content)}
                        >
                          Nusxa
                        </button>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}

            {steps.length > 0 && (
              <div className="trace">
                <AnimatePresence>
                  {steps.map((s) => (
                    <motion.div
                      key={s.id}
                      className={`step ${s.kind}`}
                      initial={stepInitial}
                      animate={stepAnimate}
                    >
                      <span className="ico">{iconForStep(s.kind)}</span>
                      <span>{s.label}</span>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}

            {streaming && (
              <div className="msg">
                <div className="avatar ai">A</div>
                <div className="bubble">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="composer-wrap">
        <div className="composer">
          <textarea
            ref={taRef}
            style={textareaStyle}
            rows={1}
            placeholder={
              mode === "agent"
                ? "Agentga vazifa bering — u tugatguncha ishlaydi..."
                : "Xabar yozing..."
            }
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              grow()
            }}
            onKeyDown={onKey}
          />
          <div className="composer-row">
            {skills.slice(0, 4).map((s) => (
              <button
                key={s.id}
                className={`chip ${activeSkill === s.id ? "active" : ""}`}
                onClick={() => onPickSkill(activeSkill === s.id ? null : s.id)}
              >
                <span>{s.icon}</span>
                <span>{s.name}</span>
              </button>
            ))}
            <button
              className={`icon-btn mic ${listening ? "active" : ""}`}
              title="Ovozli kiritish"
              onClick={toggleMic}
            >
              {"\uD83C\uDFA4"}
            </button>
            {streaming ? (
              <button className="send" onClick={onStop} title="To'xtatish">
                {"\u25A0"}
              </button>
            ) : (
              <button className="send" onClick={submit} disabled={!text.trim()}>
                {"\u2191"}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

const heroLogoStyle: CSSProperties = {
  width: 54,
  height: 54,
  borderRadius: 14,
  fontSize: 26,
}

function iconForStep(kind: string): string {
  const map: Record<string, string> = {
    reasoning: "\uD83E\uDDE0",
    strategy: "\uD83C\uDFAF",
    tool: "\uD83D\uDD27",
    validation: "\u2705",
    iteration: "\uD83D\uDD01",
    stage: "\u25B8",
    final: "\u2728",
    metrics: "\uD83D\uDCCA",
  }
  return map[kind] || "\u2022"
}
