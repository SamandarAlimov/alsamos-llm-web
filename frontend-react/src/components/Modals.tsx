import { useState } from "react"
import type { CSSProperties } from "react"
import { motion } from "framer-motion"
import { api } from "../api"
import type { Project, Skill } from "../types"

const overlayInitial = { opacity: 0 }
const overlayAnimate = { opacity: 1 }
const modalInitial = { opacity: 0, y: 16, scale: 0.98 }
const modalAnimate = { opacity: 1, y: 0, scale: 1 }
const rightStyle: CSSProperties = { display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }
const listStyle: CSSProperties = { maxHeight: 240, overflowY: "auto", marginBottom: 12 }

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <motion.div className="overlay" initial={overlayInitial} animate={overlayAnimate}>
      <motion.div className="modal" initial={modalInitial} animate={modalAnimate}>
        {children}
      </motion.div>
    </motion.div>
  )
}

/* ---------- Login ---------- */
export function LoginModal({ onLogin }: { onLogin: (token: string) => void }) {
  const [pass, setPass] = useState("")
  const [err, setErr] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setErr("")
    try {
      const token = await api.login(pass)
      onLogin(token)
    } catch {
      setErr("Parol noto'g'ri.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <Overlay>
      <h2>Alsamos AI</h2>
      <p className="desc">Davom etish uchun kirish parolini kiriting.</p>
      <div className="field">
        <input
          className="input"
          type="password"
          placeholder="Parol"
          value={pass}
          onChange={(e) => setPass(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
      </div>
      {err && <div className="err-text">{err}</div>}
      <div style={rightStyle}>
        <button className="btn" onClick={submit} disabled={busy}>
          {busy ? "Tekshirilmoqda..." : "Kirish"}
        </button>
      </div>
    </Overlay>
  )
}

/* ---------- Projects ---------- */
interface ProjectsProps {
  projects: Project[]
  onClose: () => void
  onChanged: () => void
}
export function ProjectsModal({ projects, onClose, onChanged }: ProjectsProps) {
  const [name, setName] = useState("")
  const [instr, setInstr] = useState("")
  const [busy, setBusy] = useState(false)

  async function create() {
    if (!name.trim() || busy) return
    setBusy(true)
    try {
      await api.createProject(name.trim(), instr.trim())
      setName("")
      setInstr("")
      onChanged()
    } finally {
      setBusy(false)
    }
  }
  async function remove(id: string) {
    await api.deleteProject(id)
    onChanged()
  }

  return (
    <Overlay>
      <h2>Loyihalar</h2>
      <p className="desc">
        Har bir loyiha o'z ko'rsatmalari (context) bilan ishlaydi — suhbatlar avtomatik
        shu ko'rsatmalarni oladi.
      </p>
      <div style={listStyle}>
        {projects.map((p) => (
          <div key={p.id} className="skill-card">
            <div className="row">
              <div style={growCol}>
                <div className="t">{p.name}</div>
                <div className="d">{p.instructions || "Ko'rsatmasiz"}</div>
              </div>
              <button className="mini-btn" onClick={() => remove(p.id)}>
                O'chirish
              </button>
            </div>
          </div>
        ))}
        {projects.length === 0 && <p className="desc">Hozircha loyiha yo'q.</p>}
      </div>
      <div className="field">
        <label>Yangi loyiha nomi</label>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="field">
        <label>Ko'rsatmalar (ixtiyoriy)</label>
        <textarea
          className="textarea"
          value={instr}
          onChange={(e) => setInstr(e.target.value)}
          placeholder="Masalan: Har doim rasmiy o'zbek tilida, qisqa javob ber."
        />
      </div>
      <div style={rightStyle}>
        <button className="btn secondary" onClick={onClose}>
          Yopish
        </button>
        <button className="btn" onClick={create} disabled={busy || !name.trim()}>
          Qo'shish
        </button>
      </div>
    </Overlay>
  )
}

/* ---------- Skills ---------- */
interface SkillsProps {
  skills: Skill[]
  onClose: () => void
  onChanged: () => void
}
export function SkillsModal({ skills, onClose, onChanged }: SkillsProps) {
  const [name, setName] = useState("")
  const [desc, setDesc] = useState("")
  const [sys, setSys] = useState("")
  const [busy, setBusy] = useState(false)

  async function create() {
    if (!name.trim() || !sys.trim() || busy) return
    setBusy(true)
    try {
      await api.createSkill({ name: name.trim(), description: desc.trim(), system: sys.trim() })
      setName("")
      setDesc("")
      setSys("")
      onChanged()
    } finally {
      setBusy(false)
    }
  }
  async function remove(id: string) {
    await api.deleteSkill(id)
    onChanged()
  }

  return (
    <Overlay>
      <h2>Skills — ko'nikmalar</h2>
      <p className="desc">
        Skill — qayta ishlatiladigan mutaxassislik. Suhbatda tanlab, AI'ga aniq rol berasiz.
      </p>
      <div style={listStyle}>
        {skills.map((s) => (
          <div key={s.id} className="skill-card">
            <div className="row">
              <div style={growCol}>
                <div className="t">
                  {s.icon} {s.name} {s.builtin ? "" : "(shaxsiy)"}
                </div>
                <div className="d">{s.description}</div>
              </div>
              {!s.builtin && (
                <button className="mini-btn" onClick={() => remove(s.id)}>
                  O'chirish
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="field">
        <label>Yangi skill nomi</label>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="field">
        <label>Tavsif</label>
        <input className="input" value={desc} onChange={(e) => setDesc(e.target.value)} />
      </div>
      <div className="field">
        <label>System prompt (rol)</label>
        <textarea className="textarea" value={sys} onChange={(e) => setSys(e.target.value)} />
      </div>
      <div style={rightStyle}>
        <button className="btn secondary" onClick={onClose}>
          Yopish
        </button>
        <button className="btn" onClick={create} disabled={busy || !name.trim() || !sys.trim()}>
          Qo'shish
        </button>
      </div>
    </Overlay>
  )
}

const growCol: CSSProperties = { flex: 1, minWidth: 0 }
