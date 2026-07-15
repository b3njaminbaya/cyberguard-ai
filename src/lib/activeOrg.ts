const STORAGE_KEY = "cyberguard.activeOrgId"
const listeners = new Set<() => void>()

export function getActiveOrgId(): string | null {
  return localStorage.getItem(STORAGE_KEY)
}

export function setActiveOrgId(orgId: string | null) {
  if (orgId) localStorage.setItem(STORAGE_KEY, orgId)
  else localStorage.removeItem(STORAGE_KEY)
  listeners.forEach((l) => l())
}

export function subscribeActiveOrg(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
