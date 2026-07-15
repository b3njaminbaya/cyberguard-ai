import { useState } from "react"
import { Building2, ChevronDown, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useOrg, slugify } from "@/lib/OrgContext"

export function OrgSwitcher() {
  const { organizations, activeOrg, switchOrg, createOrg } = useOrg()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [name, setName] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleCreate = async () => {
    setSubmitting(true)
    setError(null)
    const { error } = await createOrg(name.trim(), slugify(name))
    setSubmitting(false)
    if (error) {
      setError(error)
      return
    }
    setName("")
    setDialogOpen(false)
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-2">
            <Building2 className="h-4 w-4" />
            {activeOrg?.name ?? "Select organization"}
            <ChevronDown className="h-3 w-3 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuLabel>Organizations</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {organizations.map((org) => (
            <DropdownMenuItem key={org.id} onClick={() => switchOrg(org.id)} className="flex items-center justify-between">
              <span>{org.name}</span>
              {org.id === activeOrg?.id && <span className="text-xs text-primary">active</span>}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create organization
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create organization</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="org-name">Organization name</Label>
            <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Security" />
            {name && <p className="text-xs text-muted-foreground">Slug: {slugify(name) || "—"}</p>}
            {error && <p className="text-sm text-critical">{error}</p>}
          </div>
          <DialogFooter>
            <Button disabled={!name.trim() || submitting} onClick={handleCreate}>
              {submitting ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
