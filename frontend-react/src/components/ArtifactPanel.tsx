import { useMemo, useState } from "react"
import type { CSSProperties } from "react"
import { motion } from "framer-motion"
import type { Artifact } from "../types"
import { highlight } from "../lib/markdown"

interface Props {
  artifact: Artifact
  onClose: () => void
  onSave?: (content: string) => void
}

type Tab = "preview" | "code"

const mInitial = { opacity: 0, x: 24 }
const mAnimate = { opacity: 1, x: 0 }
const mExit = { opacity: 0, x: 24 }
const mTransition = { duration: 0.22 }
const editAreaStyle: CSSProperties = { height: "100%", border: "none", borderRadius: 0 }
const footerStyle: CSSProperties = {
  borderTop: "1px solid var(--border)",
  borderBottom: "none",
  gap: 8,
}

function canPreview(a: Artifact): boolean {
  return a.type === "html" || a.type === "svg"
}

export default function ArtifactPanel({ artifact, onClose, onSave }: Props) {
  const [tab, setTab] = useState<Tab>(canPreview(artifact) ? "preview" : "code")
  const [draft, setDraft] = useState<string>(artifact.content)
  const [editing, setEditing] = useState(false)

  const htmlObj = useMemo(
    () => ({ __html: highlight(artifact.content, artifact.language) }),
    [artifact.content, artifact.language],
  )

  const previewDoc = useMemo(() => {
    if (artifact.type === "svg") {
      return `<!doctype html><html><body style="margin:0;display:grid;place-items:center;height:100vh;background:#fff">${artifact.content}</body></html>`
    }
    return artifact.content
  }, [artifact.content, artifact.type])

  function copy() {
    navigator.clipboard.writeText(artifact.content).catch(() => undefined)
  }
  function download() {
    const blob = new Blob([artifact.content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = artifact.title.replace(/\s+/g, "_") + extFor(artifact.language)
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <motion.section
      className="artifact"
      initial={mInitial}
      animate={mAnimate}
      exit={mExit}
      transition={mTransition}
    >
      <div className="artifact-head">
        <span>{iconFor(artifact.type)}</span>
        <div className="artifact-title">{artifact.title}</div>
        {canPreview(artifact) && (
          <div className="tabs">
            <button
              className={`tab ${tab === "preview" ? "active" : ""}`}
              onClick={() => setTab("preview")}
            >
              Ko'rinish
            </button>
            <button
              className={`tab ${tab === "code" ? "active" : ""}`}
              onClick={() => setTab("code")}
            >
              Kod
            </button>
          </div>
        )}
        <button className="icon-btn" title="Nusxa" onClick={copy}>
          {"\u2398"}
        </button>
        <button className="icon-btn" title="Yuklab olish" onClick={download}>
          {"\u2193"}
        </button>
        <button className="icon-btn" title="Yopish" onClick={onClose}>
          {"\u2715"}
        </button>
      </div>

      <div className="artifact-body">
        {tab === "preview" && canPreview(artifact) ? (
          <iframe title="artifact-preview" sandbox="allow-scripts" srcDoc={previewDoc} />
        ) : editing ? (
          <textarea
            className="textarea"
            style={editAreaStyle}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        ) : (
          <pre>
            <code dangerouslySetInnerHTML={htmlObj} />
          </pre>
        )}
      </div>

      {onSave && (
        <div className="artifact-head" style={footerStyle}>
          {editing ? (
            <>
              <button
                className="btn"
                onClick={() => {
                  onSave(draft)
                  setEditing(false)
                }}
              >
                Saqlash
              </button>
              <button className="btn secondary" onClick={() => setEditing(false)}>
                Bekor
              </button>
            </>
          ) : (
            <button className="btn secondary" onClick={() => setEditing(true)}>
              Tahrirlash
            </button>
          )}
        </div>
      )}
    </motion.section>
  )
}

function iconFor(type: Artifact["type"]): string {
  const map: Record<string, string> = {
    html: "\uD83C\uDF10",
    svg: "\uD83D\uDDBC\uFE0F",
    react: "\u269B\uFE0F",
    markdown: "\uD83D\uDCC4",
    mermaid: "\uD83D\uDCCA",
    code: "\uD83D\uDCBB",
  }
  return map[type] || "\uD83D\uDCBB"
}

function extFor(lang: string): string {
  const map: Record<string, string> = {
    python: ".py",
    javascript: ".js",
    typescript: ".ts",
    tsx: ".tsx",
    jsx: ".jsx",
    html: ".html",
    css: ".css",
    svg: ".svg",
    json: ".json",
  }
  return map[lang] || ".txt"
}
