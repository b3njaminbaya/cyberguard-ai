import { createContext, useContext, useEffect, useState, useSyncExternalStore, type ReactNode } from "react"
import { orgClient } from "@/lib/auth-client"
import { useAuth } from "@/lib/AuthContext"
import { getActiveOrgId, setActiveOrgId, subscribeActiveOrg } from "@/lib/activeOrg"

export interface Organization {
  id: string
  name: string
  slug: string
}

interface OrgContextValue {
  organizations: Organization[]
  activeOrgId: string | null
  activeOrg: Organization | null
  isLoading: boolean
  switchOrg: (orgId: string) => Promise<void>
  createOrg: (name: string, slug: string) => Promise<{ error: string | null }>
  refetch: () => Promise<void>
}

const OrgContext = createContext<OrgContextValue | null>(null)

function slugify(name: string) {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")
}

export function OrgProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const activeOrgId = useSyncExternalStore(subscribeActiveOrg, getActiveOrgId, () => null)

  const loadOrgs = async () => {
    if (!user) {
      setOrganizations([])
      setIsLoading(false)
      return
    }
    setIsLoading(true)
    const { data } = await orgClient.organization.list()
    const orgs = (data ?? []) as Organization[]
    setOrganizations(orgs)

    const current = getActiveOrgId()
    const stillValid = current && orgs.some((o) => o.id === current)
    if (!stillValid && orgs.length > 0) {
      setActiveOrgId(orgs[0].id)
      await orgClient.organization.setActive({ organizationId: orgs[0].id })
    } else if (orgs.length === 0) {
      setActiveOrgId(null)
    }
    setIsLoading(false)
  }

  useEffect(() => {
    loadOrgs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id])

  const switchOrg = async (orgId: string) => {
    await orgClient.organization.setActive({ organizationId: orgId })
    setActiveOrgId(orgId)
  }

  const createOrg = async (name: string, slug: string) => {
    const { data, error } = await orgClient.organization.create({ name, slug })
    if (error) return { error: error.message ?? "Failed to create organization" }
    await loadOrgs()
    if (data?.id) await switchOrg(data.id)
    return { error: null }
  }

  const activeOrg = organizations.find((o) => o.id === activeOrgId) ?? null

  return (
    <OrgContext.Provider value={{ organizations, activeOrgId, activeOrg, isLoading, switchOrg, createOrg, refetch: loadOrgs }}>
      {children}
    </OrgContext.Provider>
  )
}

export function useOrg() {
  const ctx = useContext(OrgContext)
  if (!ctx) throw new Error("useOrg must be used within OrgProvider")
  return ctx
}

export { slugify }
