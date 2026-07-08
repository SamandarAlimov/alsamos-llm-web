import { marked } from "marked"
import hljs from "highlight.js"
import type { ArtifactType } from "../types"

marked.setOptions({ gfm: true, breaks: true })

export function renderMarkdown(text: string): string {
  const raw = marked.parse(text ?? "", { async: false }) as string
  return raw
}

export function highlight(code: string, language?: string): string {
  try {
    if (language && hljs.getLanguage(language)) {
      return hljs.highlight(code, { language }).value
    }
    return hljs.highlightAuto(code).value
  } catch {
    return escapeHtml(code)
  }
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
}

export interface DetectedArtifact {
  title: string
  type: ArtifactType
  language: string
  content: string
}

const LANG_TO_TYPE: Record<string, ArtifactType> = {
  html: "html",
  svg: "svg",
  xml: "svg",
  markdown: "markdown",
  md: "markdown",
  mermaid: "mermaid",
  jsx: "react",
  tsx: "react",
}

/**
 * Javobdagi eng katta kod blokini artifact sifatida aniqlaydi.
 * Uzun kod (>= 8 qator yoki html/svg) alohida panelda ko'rsatishga arziydi.
 */
export function detectArtifact(text: string): DetectedArtifact | null {
  const fence = /```([\w+-]*)\n([\s\S]*?)```/g
  let best: DetectedArtifact | null = null
  let bestLen = 0
  let m: RegExpExecArray | null
  while ((m = fence.exec(text)) !== null) {
    const lang = (m[1] || "").toLowerCase()
    const content = m[2].trim()
    const lines = content.split("\n").length
    const isRich = lang === "html" || lang === "svg"
    if ((lines >= 8 || isRich) && content.length > bestLen) {
      bestLen = content.length
      const type = LANG_TO_TYPE[lang] || "code"
      best = {
        title: titleFor(type, lang),
        type,
        language: lang || "text",
        content,
      }
    }
  }
  return best
}

function titleFor(type: ArtifactType, lang: string): string {
  if (type === "html") return "HTML sahifa"
  if (type === "svg") return "SVG grafika"
  if (type === "react") return "React komponent"
  if (type === "markdown") return "Hujjat"
  if (type === "mermaid") return "Diagramma"
  return `${lang || "Kod"} snippet`
}
