import { useCallback, useEffect, useRef, useState } from "react"
import type { CSSProperties } from "react"
import { AnimatePresence } from "framer-motion"
import Sidebar from "./components/Sidebar"
import ChatPanel from "./components/ChatPanel"
import type { AgentStep } from "./components/ChatPanel"
import ArtifactPanel from "./components/ArtifactPanel"
import { ImageStudio, VideoStudio } from "./components/Studios"
import { LoginModal, ProjectsModal, SkillsModal } from "./components/Modals"
import { api, ApiError, getToken, setToken } from "./api"
import { streamPost } from "./sse"
import { detectArtifact } from "./lib/markdown"
import type {
  Artifact,
  ChatMessage,
  Mode,
  ModelInfo,
  Project,
  Skill,
} from "./types"

const topRight: CSSProperties = { marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }

export default function App() {
  const [needLogin, setNeedLogin] = useState(false)
  const [ready, setReady] = useState(false)

  const [mode, setMode] = useState<Mode>("chat")
  const [models, setModels] = useState<ModelInfo[]>([])
  const [model, setModel] = useState<string>("")
  const [projects, setProjects] = useState<Project[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [activeProject, setActiveProject] = useState<string | null>(null)
  const [activeSkill, setActiveSkill] = useState<string | null>(null)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [steps, setSteps] = useState<AgentStep[]>([])
  const [streaming, setStreaming] = useState(false)
  const [artifact, setArtifact] = useState<Artifact | null>(null)

  const [theme, setTheme] = useState<string>(localStorage.getItem("alsamos-theme") || "dark")
  const [showProjects, setShowProjects] = useState(false)
  const [showSkills, setShowSkills] = useState(false)
  const [ttsVoice] = useState("Brian")

  const ctrlRef = useRef<{ cancel: () => void } | null>(null)
  const stepId = useRef(0)

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("alsamos-theme", theme)
  }, [theme])

  const loadData = useCallback(async () => {
    const [m, ps, ss] = await Promise.all([api.models(), api.listProjects(), api.listSkills()])
    setModels(m.models)
    const textModels = m.models.filter((x) => x.kind === "text")
    if (textModels[0]) setModel((prev) => prev || textModels[0].id)
    setProjects(ps)
    setSkills(ss)
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        const h = await api.health()
        if (h.auth_required && !getToken()) {
          setNeedLogin(true)
          return
        }
        await loadData()
        setReady(true)
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) setNeedLogin(true)
      }
    })()
  }, [loadData])

  function onLoggedIn(token: string) {
    setToken(token)
    setNeedLogin(false)
    loadData().then(() => setReady(true))
  }

  const pushStep = useCallback((kind: string, label: string) => {
    stepId.current += 1
    setSteps((prev) => [...prev, { id: stepId.current, kind, label }])
  }, [])

  function stop() {
    ctrlRef.current?.cancel()
    setStreaming(false)
  }

  const finalizeArtifact = useCallback((content: string) => {
    const det = detectArtifact(content)
    if (det) {
      setArtifact({
        id: "local_" + Date.now(),
        title: det.title,
        type: det.type,
        language: det.language,
        content: det.content,
        versions: [],
        created: Date.now(),
        updated: Date.now(),
      })
    }
  }, [])

  const sendChat = useCallback(
    (text: string) => {
      const history = messages.filter((m) => m.role !== "system")
      const next: ChatMessage[] = [...history, { role: "user", content: text }]
      setMessages([...next, { role: "assistant", content: "" }])
      setStreaming(true)
      let acc = ""
      ctrlRef.current = streamPost(
        "/api/chat",
        {
          model,
          messages: next,
          project_id: activeProject,
          skill_id: activeSkill,
        },
        {
          onToken: (t) => {
            acc += t
            setMessages((prev) => {
              const copy = [...prev]
              copy[copy.length - 1] = { role: "assistant", content: acc }
              return copy
            })
          },
          onDone: () => {
            setStreaming(false)
            finalizeArtifact(acc)
          },
          onError: (msg) => {
            setStreaming(false)
            setMessages((prev) => {
              const copy = [...prev]
              copy[copy.length - 1] = { role: "assistant", content: "\u26A0\uFE0F " + msg }
              return copy
            })
          },
        },
      )
    },
    [messages, model, activeProject, activeSkill, finalizeArtifact],
  )

  const sendAgent = useCallback(
    (text: string) => {
      const history = messages.filter((m) => m.role !== "system")
      setMessages([...history, { role: "user", content: text }])
      setSteps([])
      stepId.current = 0
      setStreaming(true)
      let finalOut = ""
      ctrlRef.current = streamPost(
        "/api/agent",
        {
          model,
          task: text,
          history,
          use_tools: true,
          project_id: activeProject,
          skill_id: activeSkill,
        },
        {
          onEvent: (evt) => {
            const e = evt as Record<string, any>
            switch (e.type) {
              case "reasoning":
                pushStep("reasoning", "Fikrlash: " + short(e.summary || e.text || e.plan))
                break
              case "strategy":
                pushStep("strategy", "Strategiya: " + short(e.name || e.strategy || e.rationale))
                break
              case "iteration":
                pushStep("iteration", "Urinish " + (e.n ?? e.iteration ?? ""))
                break
              case "tool":
                pushStep(
                  "tool",
                  "Tool: " + (e.name || "") + " (" + (e.phase || "") + ")",
                )
                break
              case "validation":
                pushStep(
                  "validation",
                  "Tekshiruv: " + (e.level || "") + (e.passed ? " \u2014 o'tdi" : ""),
                )
                break
              case "stage":
                pushStep("stage", short(e.label || e.stage || ""))
                break
              case "final":
                finalOut = String(e.output ?? "")
                pushStep("final", "Yakunlandi (sifat: " + (e.quality ?? "-") + ")")
                break
              case "metrics":
                pushStep("metrics", "Ko'rsatkichlar yangilandi")
                break
              default:
                break
            }
          },
          onDone: () => {
            setStreaming(false)
            if (finalOut) {
              setMessages((prev) => [...prev, { role: "assistant", content: finalOut }])
              finalizeArtifact(finalOut)
            }
          },
          onError: (msg) => {
            setStreaming(false)
            setMessages((prev) => [...prev, { role: "assistant", content: "\u26A0\uFE0F " + msg }])
          },
        },
      )
    },
    [messages, model, activeProject, activeSkill, pushStep, finalizeArtifact],
  )

  const onSend = useCallback(
    (text: string) => {
      if (mode === "agent") sendAgent(text)
      else sendChat(text)
    },
    [mode, sendAgent, sendChat],
  )

  function newChat() {
    stop()
    setMessages([])
    setSteps([])
    setArtifact(null)
  }

  const activeProjectName = projects.find((p) => p.id === activeProject)?.name
  const textModels = models.filter((m) => m.kind === "text")

  if (needLogin) return <LoginModal onLogin={onLoggedIn} />
  if (!ready)
    return (
      <div className="hero">
        <div className="spinner" />
      </div>
    )

  return (
    <div className={"app" + (artifact ? " with-artifact" : "")}>
      <Sidebar
        mode={mode}
        setMode={setMode}
        projects={projects}
        activeProject={activeProject}
        setActiveProject={setActiveProject}
        onNewChat={newChat}
        onManageProjects={() => setShowProjects(true)}
        onManageSkills={() => setShowSkills(true)}
      />

      <div className="main">
        <div className="topbar">
          {(mode === "chat" || mode === "agent") && (
            <select className="select" value={model} onChange={(e) => setModel(e.target.value)}>
              {textModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          )}
          {activeProjectName && <span className="pill">{"\uD83D\uDCC1 " + activeProjectName}</span>}
          {activeSkill && (
            <span className="pill">
              {skills.find((s) => s.id === activeSkill)?.name}
            </span>
          )}
          <div style={topRight}>
            <button
              className="icon-btn"
              title="Mavzu"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19"}
            </button>
          </div>
        </div>

        {mode === "image" ? (
          <ImageStudio />
        ) : mode === "video" ? (
          <VideoStudio />
        ) : (
          <ChatPanel
            mode={mode}
            messages={messages}
            steps={steps}
            streaming={streaming}
            skills={skills}
            activeSkill={activeSkill}
            onPickSkill={setActiveSkill}
            onSend={onSend}
            onStop={stop}
            ttsVoice={ttsVoice}
          />
        )}
      </div>

      <AnimatePresence>
        {artifact && (
          <ArtifactPanel
            key={artifact.id}
            artifact={artifact}
            onClose={() => setArtifact(null)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showProjects && (
          <ProjectsModal
            projects={projects}
            onClose={() => setShowProjects(false)}
            onChanged={() => api.listProjects().then(setProjects)}
          />
        )}
        {showSkills && (
          <SkillsModal
            skills={skills}
            onClose={() => setShowSkills(false)}
            onChanged={() => api.listSkills().then(setSkills)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function short(v: unknown, n = 90): string {
  const s = String(v ?? "")
  return s.length > n ? s.slice(0, n) + "\u2026" : s
}
