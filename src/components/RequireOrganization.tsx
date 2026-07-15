import { useState, type ReactNode } from "react"
import { Building2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { useAuth } from "@/lib/AuthContext"
import { useOrg, slugify } from "@/lib/OrgContext"

/** Every data endpoint requires an active organization (X-Organization-Id).
 * A freshly signed-up user has none yet — Neon Auth's real `organization`
 * plugin has no concept of a default org, so we ask them to create one
 * before rendering the dashboard, rather than silently failing every query. */
export function RequireOrganization({ children }: { children: ReactNode }) {
  const { signOut } = useAuth()
  const { organizations, isLoading, createOrg } = useOrg()
  const [name, setName] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading your organizations…</div>
  }

  if (organizations.length > 0) return <>{children}</>

  const handleCreate = async () => {
    setSubmitting(true)
    setError(null)
    const { error } = await createOrg(name.trim(), slugify(name))
    setSubmitting(false)
    if (error) setError(error)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-matrix p-6">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1">
          <div className="flex items-center gap-2">
            <Building2 className="h-6 w-6 text-primary" />
            <CardTitle>Create your organization</CardTitle>
          </div>
          <CardDescription>
            CyberGuard AI is multi-tenant — every account belongs to at least one organization, which scopes all of
            your data.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="org-name">Organization name</Label>
            <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Security" autoFocus />
            {name && <p className="text-xs text-muted-foreground">Slug: {slugify(name) || "—"}</p>}
          </div>
          {error && <p className="text-sm text-critical">{error}</p>}
          <Button className="w-full" disabled={!name.trim() || submitting} onClick={handleCreate}>
            {submitting ? "Creating…" : "Create organization"}
          </Button>
          <button type="button" className="text-sm text-muted-foreground hover:text-foreground w-full text-center" onClick={signOut}>
            Sign out
          </button>
        </CardContent>
      </Card>
    </div>
  )
}
