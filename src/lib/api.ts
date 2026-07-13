import { getAccessToken } from "@/lib/auth-client"

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getAccessToken()
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, body?.detail ?? `${path} failed: ${res.status} ${res.statusText}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export interface ThreatDto {
  id: string
  score: number
  label: string
  severity: string
  summary: string | null
  created_at: string
  event_id: string
  source_ip: string | null
  dest_ip: string | null
  protocol: string | null
  bytes: number | null
}

export interface EventDto {
  id: string
  ts: string
  source_ip: string
  dest_ip: string
  protocol: string
  bytes: number
  threats: ThreatDto[]
}

export interface SummaryDto {
  total_events: number
  total_threats: number
  by_severity: { critical: number; high: number; medium: number }
  by_category: Record<string, number>
  by_protocol: Record<string, number>
}

export interface ModelMetricsDto {
  trained: boolean
  trained_at: string | null
  accuracy: number | null
  macro_f1: number | null
  weighted_f1: number | null
  per_class: Record<string, { precision: number; recall: number; "f1-score": number; support: number }>
}

export interface MeDto {
  id: string
  email: string
  role: string
}

export interface NotificationSettingsDto {
  id: string
  notifications_enabled: boolean
  email_enabled: boolean
  email_recipients: string
  slack_enabled: boolean
  slack_webhook_url: string | null
  slack_channel: string | null
  webhook_enabled: boolean
  webhook_url: string | null
  webhook_secret: string | null
  alert_on_critical: boolean
  alert_on_high: boolean
  alert_on_medium: boolean
  updated_at: string
}

export type NotificationSettingsInput = Omit<NotificationSettingsDto, "id" | "updated_at">

export const api = {
  threats: (limit = 50) => request<ThreatDto[]>(`/threats?limit=${limit}`),
  events: (limit = 50) => request<EventDto[]>(`/events?limit=${limit}`),
  summary: () => request<SummaryDto>("/stats/summary"),
  modelMetrics: () => request<ModelMetricsDto>("/model/metrics"),
  me: () => request<MeDto>("/users/me"),
  notificationSettings: () => request<NotificationSettingsDto>("/settings/notifications"),
  saveNotificationSettings: (payload: NotificationSettingsInput) =>
    request<NotificationSettingsDto>("/settings/notifications", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  testSlack: () => request<{ status: string }>("/settings/notifications/test/slack", { method: "POST" }),
  testEmail: () => request<{ status: string }>("/settings/notifications/test/email", { method: "POST" }),
  testWebhook: () => request<{ status: string }>("/settings/notifications/test/webhook", { method: "POST" }),
  triageThreat: (threatId: string, regenerate = false) =>
    request<ThreatDto>(`/threats/${threatId}/triage${regenerate ? "?regenerate=true" : ""}`, { method: "POST" }),
}
