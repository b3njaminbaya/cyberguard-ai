const STORAGE_KEY = "cyberguard.realtimeUpdates"
const listeners = new Set<() => void>()

export function getRealtimeEnabled(): boolean {
  return localStorage.getItem(STORAGE_KEY) !== "false"
}

export function setRealtimeEnabled(enabled: boolean) {
  localStorage.setItem(STORAGE_KEY, String(enabled))
  listeners.forEach((l) => l())
}

export function subscribeRealtimePreference(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
