import { motion } from "framer-motion"
import type { CSSProperties } from "react"
import type { Mode, Project } from "../types"

interface Props {
  mode: Mode
  setMode: (m: Mode) => void
  projects: Project[]
  activeProject: string | null
  setActiveProject: (id: string | null) => void
  onNewChat: () => void
  onManageProjects: () => void
  onManageSkills: () => void
}

const MODES: { id: Mode; icon: string; label: string }[] = [
  { id: "chat", icon: "\uD83D\uDCAC", label: "Suhbat" },
  { id: "agent", icon: "\uD83E\uDDE0", label: "Agent" },
  { id: "image", icon: "\uD83C\uDFA8", label: "Rasm studiya" },
  { id: "video", icon: "\uD83C\uDFAC", label: "Video studiya" },
]

const newChatStyle: CSSProperties = { width: "100%", marginBottom: 6 }
const spacerStyle: CSSProperties = { height: 6 }
const itemStyle: CSSProperties = {
  width: "100%",
  border: "none",
  background: "transparent",
  textAlign: "left",
}

export default function Sidebar({
  mode,
  setMode,
  projects,
  activeProject,
  setActiveProject,
  onNewChat,
  onManageProjects,
  onManageSkills,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logo">A</div>
        <div>
          <div className="name">Alsamos AI</div>
          <div className="sub">Corporation Intelligence</div>
        </div>
      </div>

      <button className="btn" style={newChatStyle} onClick={onNewChat}>
        + Yangi suhbat
      </button>

      <div style={spacerStyle} />
      {MODES.map((m) => (
        <button
          key={m.id}
          className={`nav-btn ${mode === m.id ? "active" : ""}`}
          onClick={() => setMode(m.id)}
        >
          <span>{m.icon}</span>
          <span>{m.label}</span>
        </button>
      ))}

      <div className="side-label">Loyihalar</div>
      <button
        className={`side-item ${!activeProject ? "active" : ""}`}
        onClick={() => setActiveProject(null)}
        style={itemStyle}
      >
        <span>{"\u2014 Loyihasiz"}</span>
      </button>
      {projects.map((p) => (
        <motion.button
          key={p.id}
          layout
          className={`side-item ${activeProject === p.id ? "active" : ""}`}
          onClick={() => setActiveProject(p.id)}
          style={itemStyle}
        >
          <span>{"\uD83D\uDCC1 " + p.name}</span>
        </motion.button>
      ))}

      <button className="nav-btn" onClick={onManageProjects}>
        <span>{"\u2699\uFE0F"}</span>
        <span>Loyihalarni boshqarish</span>
      </button>

      <div className="spacer" />
      <button className="nav-btn" onClick={onManageSkills}>
        <span>{"\u2728"}</span>
        <span>Skills (ko'nikmalar)</span>
      </button>
    </aside>
  )
}
