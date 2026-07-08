import { useState } from "react"
import type { CSSProperties } from "react"
import { motion } from "framer-motion"
import { api } from "../api"
import type { StoryboardFrame } from "../types"

const cardInitial = { opacity: 0, scale: 0.96 }
const cardAnimate = { opacity: 1, scale: 1 }
const rowStyle: CSSProperties = { gap: 8, marginTop: 12 }
const growStyle: CSSProperties = { flex: 1 }

export function ImageStudio() {
  const [prompt, setPrompt] = useState("")
  const [busy, setBusy] = useState(false)
  const [images, setImages] = useState<string[]>([])
  const [err, setErr] = useState("")

  async function generate() {
    if (!prompt.trim() || busy) return
    setBusy(true)
    setErr("")
    try {
      const r = await api.image(prompt.trim())
      setImages((prev) => [r.url, ...prev])
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="studio">
      <h1 style={titleStyle}>{"\uD83C\uDFA8 Rasm studiya"}</h1>
      <p style={dimStyle}>Bepul model (Flux) bilan matndan rasm yarating.</p>
      <div className="row" style={rowStyle}>
        <input
          className="input"
          style={growStyle}
          placeholder="Rasm tavsifi... masalan: Toshkent, kelajak shahri, neon"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && generate()}
        />
        <button className="btn" onClick={generate} disabled={busy || !prompt.trim()}>
          {busy ? "Yaratilmoqda..." : "Yaratish"}
        </button>
      </div>
      {err && <div className="err-text">{err}</div>}
      <div className="grid">
        {images.map((src, i) => (
          <motion.img key={src + i} src={src} initial={cardInitial} animate={cardAnimate} />
        ))}
      </div>
    </div>
  )
}

export function VideoStudio() {
  const [prompt, setPrompt] = useState("")
  const [frames, setFrames] = useState(4)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<StoryboardFrame[]>([])
  const [playing, setPlaying] = useState(false)
  const [current, setCurrent] = useState(0)
  const [err, setErr] = useState("")

  async function generate() {
    if (!prompt.trim() || busy) return
    setBusy(true)
    setErr("")
    setResult([])
    try {
      const r = await api.storyboard(prompt.trim(), frames)
      setResult(r.frames)
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  function play() {
    if (result.length === 0) return
    setPlaying(true)
    let i = 0
    setCurrent(0)
    const timer = window.setInterval(() => {
      i += 1
      if (i >= result.length) {
        window.clearInterval(timer)
        setPlaying(false)
        return
      }
      setCurrent(i)
    }, 900)
  }

  return (
    <div className="studio">
      <h1 style={titleStyle}>{"\uD83C\uDFAC Video studiya (storyboard)"}</h1>
      <p style={dimStyle}>
        Bitta g'oyadan bir nechta kadr (frame) yaratib, slideshow-animatsiya sifatida ijro etadi.
      </p>
      <div className="row" style={rowStyle}>
        <input
          className="input"
          style={growStyle}
          placeholder="Sahna tavsifi... masalan: tog'da quyosh chiqishi"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <select
          className="select"
          value={frames}
          onChange={(e) => setFrames(Number(e.target.value))}
        >
          <option value={3}>3 kadr</option>
          <option value={4}>4 kadr</option>
          <option value={6}>6 kadr</option>
          <option value={8}>8 kadr</option>
        </select>
        <button className="btn" onClick={generate} disabled={busy || !prompt.trim()}>
          {busy ? "Yaratilmoqda..." : "Yaratish"}
        </button>
      </div>
      {err && <div className="err-text">{err}</div>}

      {result.length > 0 && (
        <>
          <div className="row" style={rowStyle}>
            <button className="btn secondary" onClick={play} disabled={playing}>
              {playing ? "Ijro etilmoqda..." : "\u25B6 Ijro etish"}
            </button>
          </div>
          <div style={playerStyle}>
            <img src={result[current]?.url} style={playerImgStyle} alt="frame" />
            <div className="cap">
              Kadr {current + 1}/{result.length}: {result[current]?.scene}
            </div>
          </div>
          <div className="grid">
            {result.map((f) => (
              <motion.div
                key={f.index}
                className="frame-card"
                initial={cardInitial}
                animate={cardAnimate}
              >
                <img src={f.url} alt={f.scene} />
                <div className="cap">{f.scene}</div>
              </motion.div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

const titleStyle: CSSProperties = { fontSize: 22, margin: "0 0 4px" }
const dimStyle: CSSProperties = { color: "var(--text-dim)", fontSize: 14 }
const playerStyle: CSSProperties = {
  marginTop: 16,
  border: "1px solid var(--border)",
  borderRadius: 12,
  overflow: "hidden",
}
const playerImgStyle: CSSProperties = { width: "100%", display: "block" }
