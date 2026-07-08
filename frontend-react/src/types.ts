export type Role = "user" | "assistant" | "system"

export interface ChatMessage {
  role: Role
  content: string
}

export interface ModelInfo {
  id: string
  name: string
  kind: "text" | "image"
  description?: string
  vision?: boolean
}

export interface Project {
  id: string
  name: string
  instructions: string
  model?: string | null
  context: { title: string; content: string }[]
  artifacts: string[]
  created: number
  updated: number
}

export interface Skill {
  id: string
  name: string
  description: string
  system: string
  tools: string[]
  icon: string
  builtin?: boolean
}

export type ArtifactType = "code" | "html" | "markdown" | "svg" | "mermaid" | "react"

export interface Artifact {
  id: string
  title: string
  type: ArtifactType
  language: string
  content: string
  project_id?: string | null
  versions: { content: string; ts: number }[]
  created: number
  updated: number
}

export interface AgentEvent {
  type: string
  [key: string]: unknown
}

export interface StoryboardFrame {
  index: number
  scene: string
  url: string
}

export interface Storyboard {
  prompt: string
  width: number
  height: number
  frames: StoryboardFrame[]
  count: number
  note: string
}

export type Mode = "chat" | "agent" | "image" | "video"
