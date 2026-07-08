import type {
  Artifact,
  ChatMessage,
  ModelInfo,
  Project,
  Skill,
  Storyboard,
} from "./types"

const _rawBase = import.meta.env.VITE_API_BASE || ""
export const API_BASE = _rawBase.endsWith("/") ? _rawBase.slice(0, -1) : _rawBase

const TOKEN_KEY = "alsamos-token"

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t)
  else localStorage.removeItem(TOKEN_KEY)
}

export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const h: Record<string, string> = { ...extra }
  const t = getToken()
  if (t) h["Authorization"] = `Bearer ${t}`
  return h
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(API_BASE + path, {
    ...init,
    headers: authHeaders({ "Content-Type": "application/json", ...((init.headers as Record<string, string>) || {}) }),
  })
  if (res.status === 401) throw new ApiError(401, "unauthorized")
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const j = await res.json()
      msg = (j as any)?.message || (j as any)?.error || msg
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg)
  }
  return (await res.json()) as T
}

export interface HealthInfo {
  status: string
  auth_required?: boolean
  api_keys?: boolean
  [k: string]: unknown
}

export const api = {
  health: () => req<HealthInfo>("/api/health"),
  models: () => req<{ models: ModelInfo[]; auth_required?: boolean; api_keys?: boolean }>("/api/models"),
  metrics: () => req<Record<string, unknown>>("/api/metrics"),

  login: async (password: string): Promise<string> => {
    const j = await req<{ token: string }>("/api/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    })
    return j.token
  },

  // Projects
  listProjects: () => req<{ projects: Project[] }>("/api/projects").then((r) => r.projects),
  createProject: (name: string, instructions: string, model?: string | null) =>
    req<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name, instructions, model }),
    }),
  updateProject: (id: string, patch: Partial<Project>) =>
    req<Project>(`/api/projects/${id}`, { method: "PUT", body: JSON.stringify(patch) }),
  deleteProject: (id: string) =>
    req<{ deleted: boolean }>(`/api/projects/${id}`, { method: "DELETE" }),

  // Skills
  listSkills: () => req<{ skills: Skill[] }>("/api/skills").then((r) => r.skills),
  createSkill: (s: Partial<Skill>) =>
    req<Skill>("/api/skills", { method: "POST", body: JSON.stringify(s) }),
  deleteSkill: (id: string) =>
    req<{ deleted: boolean }>(`/api/skills/${id}`, { method: "DELETE" }),

  // Artifacts
  listArtifacts: (projectId?: string) =>
    req<{ artifacts: Artifact[] }>(
      `/api/artifacts${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`,
    ).then((r) => r.artifacts),
  createArtifact: (a: Partial<Artifact>) =>
    req<Artifact>("/api/artifacts", { method: "POST", body: JSON.stringify(a) }),
  updateArtifact: (id: string, patch: Partial<Artifact>) =>
    req<Artifact>(`/api/artifacts/${id}`, { method: "PUT", body: JSON.stringify(patch) }),
  deleteArtifact: (id: string) =>
    req<{ deleted: boolean }>(`/api/artifacts/${id}`, { method: "DELETE" }),

  // Audio
  voices: () => req<{ voices: string[]; default: string }>("/api/audio/voices"),
  tts: (text: string, voice: string) =>
    req<{ url: string; voice: string }>("/api/audio/tts", {
      method: "POST",
      body: JSON.stringify({ text, voice }),
    }),

  // Media / video
  storyboard: (prompt: string, frames = 4) =>
    req<Storyboard>("/api/media/storyboard", {
      method: "POST",
      body: JSON.stringify({ prompt, frames }),
    }),

  // Image
  image: (prompt: string, model?: string) =>
    req<{ url: string; prompt: string }>("/api/image", {
      method: "POST",
      body: JSON.stringify({ prompt, model }),
    }),
}

export type ChatBody = {
  model?: string
  messages: ChatMessage[]
  temperature?: number
  project_id?: string | null
  skill_id?: string | null
}

export type AgentBody = {
  model?: string
  task: string
  history?: ChatMessage[]
  use_tools?: boolean
  project_id?: string | null
  skill_id?: string | null
}
