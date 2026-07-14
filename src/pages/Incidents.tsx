import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Search, Plus, Clock, User, MessageSquare, Link2 } from "lucide-react"
import { LoadingState, ErrorState } from "@/components/QueryState"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api, ApiError, type IncidentDto, type IncidentInput } from "@/lib/api"
import { toast } from "@/hooks/use-toast"

const statusColors: Record<IncidentDto["status"], string> = {
  open: "bg-info text-white",
  investigating: "bg-warning text-white",
  mitigating: "bg-high text-white",
  resolved: "bg-success text-white",
  closed: "bg-muted text-muted-foreground",
}

const severityColors: Record<IncidentDto["severity"], string> = {
  critical: "bg-critical text-white",
  high: "bg-high text-white",
  medium: "bg-medium text-white",
  low: "bg-low text-white",
}

const STATUSES: IncidentDto["status"][] = ["open", "investigating", "mitigating", "resolved", "closed"]

function formatTimestamp(timestamp: string) {
  return new Date(timestamp).toLocaleString()
}

function getTimeAgo(timestamp: string) {
  const diffMins = Math.floor((Date.now() - new Date(timestamp).getTime()) / 60000)
  if (diffMins < 1) return "Just now"
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return new Date(timestamp).toLocaleDateString()
}

export default function Incidents() {
  const { data, isPending, isError, error } = useQuery({ queryKey: ["incidents"], queryFn: api.incidents })
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [newIncidentOpen, setNewIncidentOpen] = useState(false)
  const [noteDraft, setNoteDraft] = useState("")
  const [form, setForm] = useState<IncidentInput>({ title: "", description: "", severity: "medium" })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["incidents"] })

  const createIncident = useMutation({
    mutationFn: (payload: IncidentInput) => api.createIncident(payload),
    onSuccess: () => {
      invalidate()
      setNewIncidentOpen(false)
      setForm({ title: "", description: "", severity: "medium" })
      toast({ title: "Incident created" })
    },
    onError: (err: ApiError) => toast({ title: "Couldn't create incident", description: err.message, variant: "destructive" }),
  })

  const updateIncident = useMutation({
    mutationFn: (payload: { id: string; status: IncidentDto["status"] }) => api.updateIncident(payload.id, { status: payload.status }),
    onSuccess: invalidate,
    onError: (err: ApiError) => toast({ title: "Couldn't update status", description: err.message, variant: "destructive" }),
  })

  const addNote = useMutation({
    mutationFn: (payload: { id: string; content: string }) => api.addIncidentNote(payload.id, payload.content),
    onSuccess: () => {
      invalidate()
      setNoteDraft("")
    },
    onError: (err: ApiError) => toast({ title: "Couldn't add note", description: err.message, variant: "destructive" }),
  })

  if (isPending) return <LoadingState label="Loading incidents…" />
  if (isError) return <ErrorState message={(error as Error).message} />

  const filtered = data.filter((incident) => {
    const q = searchTerm.toLowerCase()
    const matchesSearch =
      incident.title.toLowerCase().includes(q) ||
      incident.id.toLowerCase().includes(q) ||
      (incident.assignee_email ?? "").toLowerCase().includes(q)
    const matchesStatus = statusFilter === "all" || incident.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const selected = data.find((i) => i.id === selectedId) ?? null

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Incident Management</h1>
          <p className="text-muted-foreground">{data.length} incidents tracked</p>
        </div>
        <Dialog open={newIncidentOpen} onOpenChange={setNewIncidentOpen}>
          <DialogTrigger asChild>
            <Button className="bg-gradient-cyber shadow-cyber">
              <Plus className="h-4 w-4 mr-2" />
              New Incident
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Create New Incident</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="title">Title</Label>
                <Input id="title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Incident title" />
              </div>
              <div>
                <Label htmlFor="severity">Severity</Label>
                <Select value={form.severity} onValueChange={(v: IncidentDto["severity"]) => setForm({ ...form, severity: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Incident description" />
              </div>
              <Button className="w-full" disabled={!form.title || createIncident.isPending} onClick={() => createIncident.mutate(form)}>
                {createIncident.isPending ? "Creating…" : "Create Incident"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input placeholder="Search incidents..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10" />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((incident) => (
          <Card key={incident.id} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <Badge className={severityColors[incident.severity]}>{incident.severity.toUpperCase()}</Badge>
                <Badge className={statusColors[incident.status]}>{incident.status.toUpperCase()}</Badge>
              </div>
              <CardTitle className="text-lg leading-tight">{incident.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground line-clamp-2">{incident.description || "No description."}</p>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  {incident.threat_id && (
                    <div className="flex items-center gap-1">
                      <Link2 className="h-3 w-3" />
                      <span>Linked to threat</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{getTimeAgo(incident.updated_at)}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1 text-sm">
                    <User className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">{incident.assignee_email ?? "Unassigned"}</span>
                  </div>
                  <Badge variant="outline" className="text-xs">{incident.id.slice(0, 8)}</Badge>
                </div>
                <Button variant="outline" size="sm" className="w-full" onClick={() => setSelectedId(incident.id)}>
                  View Details
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && (
          <p className="text-sm text-muted-foreground col-span-full text-center py-12">
            No incidents match your filters. {data.length === 0 && "Create one, or open one from a threat's details."}
          </p>
        )}
      </div>

      <Dialog open={!!selected} onOpenChange={() => setSelectedId(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {selected && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <Badge className={severityColors[selected.severity]}>{selected.severity.toUpperCase()}</Badge>
                  <Badge className={statusColors[selected.status]}>{selected.status.toUpperCase()}</Badge>
                </div>
                <DialogTitle className="text-xl">{selected.title}</DialogTitle>
              </DialogHeader>

              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label className="text-muted-foreground">Created by</Label>
                    <p className="font-medium">{selected.created_by_email}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Assignee</Label>
                    <p className="font-medium">{selected.assignee_email ?? "Unassigned"}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Created</Label>
                    <p className="font-medium">{formatTimestamp(selected.created_at)}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Last Updated</Label>
                    <p className="font-medium">{formatTimestamp(selected.updated_at)}</p>
                  </div>
                </div>

                <div>
                  <Label className="text-muted-foreground">Description</Label>
                  <p className="mt-1">{selected.description || "No description."}</p>
                </div>

                <div className="flex items-center gap-2">
                  <Label className="text-muted-foreground whitespace-nowrap">Status</Label>
                  <Select
                    value={selected.status}
                    onValueChange={(v: IncidentDto["status"]) => updateIncident.mutate({ id: selected.id, status: v })}
                  >
                    <SelectTrigger className="w-48">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUSES.map((s) => (
                        <SelectItem key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <MessageSquare className="h-4 w-4" />
                    <Label>Activity Timeline ({selected.notes.length} notes)</Label>
                  </div>
                  <div className="space-y-3">
                    {selected.notes.map((note) => (
                      <div key={note.id} className="p-3 rounded-lg bg-muted/50 border">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium">{note.author_email}</span>
                          <span className="text-xs text-muted-foreground">{formatTimestamp(note.created_at)}</span>
                        </div>
                        <p className="text-sm">{note.content}</p>
                      </div>
                    ))}
                    {selected.notes.length === 0 && <p className="text-sm text-muted-foreground">No notes yet.</p>}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Textarea
                    placeholder="Add a note…"
                    value={noteDraft}
                    onChange={(e) => setNoteDraft(e.target.value)}
                    className="flex-1"
                    rows={2}
                  />
                  <Button
                    disabled={!noteDraft.trim() || addNote.isPending}
                    onClick={() => addNote.mutate({ id: selected.id, content: noteDraft })}
                  >
                    {addNote.isPending ? "Adding…" : "Add Note"}
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
