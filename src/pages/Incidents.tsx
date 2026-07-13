import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Search, Plus, AlertCircle, Clock, User, MessageSquare } from "lucide-react"
import { DemoDataBadge } from "@/components/DemoDataBadge"

interface Incident {
  id: string
  title: string
  severity: "critical" | "high" | "medium" | "low"
  status: "open" | "investigating" | "mitigating" | "resolved" | "closed"
  assignee: string
  createdAt: string
  updatedAt: string
  description: string
  alertCount: number
  notes: Array<{
    id: string
    author: string
    content: string
    timestamp: string
  }>
}

const mockIncidents: Incident[] = [
  {
    id: "INC-2024-001",
    title: "Massive Data Exfiltration Attempt",
    severity: "critical",
    status: "investigating",
    assignee: "Sarah Chen",
    createdAt: "2024-01-20T10:35:22Z",
    updatedAt: "2024-01-20T10:45:30Z",
    description: "Detected large-scale data transfer to external IP. Approximately 15GB of sensitive data may have been compromised.",
    alertCount: 12,
    notes: [
      {
        id: "1",
        author: "Sarah Chen",
        content: "Initiated investigation. Blocking external IP and analyzing traffic patterns.",
        timestamp: "2024-01-20T10:45:30Z"
      }
    ]
  },
  {
    id: "INC-2024-002",
    title: "Coordinated Brute Force Attack",
    severity: "high",
    status: "mitigating",
    assignee: "Alex Rodriguez",
    createdAt: "2024-01-20T09:15:10Z",
    updatedAt: "2024-01-20T10:20:15Z",
    description: "Multiple failed login attempts from distributed IPs targeting admin accounts.",
    alertCount: 5,
    notes: [
      {
        id: "1",
        author: "Alex Rodriguez",
        content: "Implemented temporary IP blocks. Reviewing authentication logs.",
        timestamp: "2024-01-20T09:30:45Z"
      },
      {
        id: "2",
        author: "Alex Rodriguez", 
        content: "Added rate limiting to login endpoints. Attack intensity decreasing.",
        timestamp: "2024-01-20T10:20:15Z"
      }
    ]
  },
  {
    id: "INC-2024-003",
    title: "Suspicious SQL Query Patterns",
    severity: "medium",
    status: "resolved",
    assignee: "Jordan Kim",
    createdAt: "2024-01-20T08:42:33Z",
    updatedAt: "2024-01-20T09:15:22Z",
    description: "Application server generating unusual database queries suggesting potential SQL injection attempt.",
    alertCount: 3,
    notes: [
      {
        id: "1",
        author: "Jordan Kim",
        content: "Identified vulnerable input field in user profile update form.",
        timestamp: "2024-01-20T08:55:12Z"
      },
      {
        id: "2",
        author: "Jordan Kim",
        content: "Applied security patch. Vulnerability closed. No data accessed.",
        timestamp: "2024-01-20T09:15:22Z"
      }
    ]
  }
]

const statusColors = {
  open: "bg-info text-white",
  investigating: "bg-warning text-white",
  mitigating: "bg-high text-white",
  resolved: "bg-success text-white",
  closed: "bg-muted text-muted-foreground"
}

const severityColors = {
  critical: "bg-critical text-white",
  high: "bg-high text-white", 
  medium: "bg-medium text-white",
  low: "bg-low text-white"
}

export default function Incidents() {
  const [incidents] = useState<Incident[]>(mockIncidents)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)
  const [newIncidentOpen, setNewIncidentOpen] = useState(false)

  const filteredIncidents = incidents.filter(incident => {
    const matchesSearch = incident.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         incident.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         incident.assignee.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === "all" || incident.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const getTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return "Just now"
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Incident Management</h1>
          <p className="text-muted-foreground">Track and manage security incidents</p>
          <div className="mt-2"><DemoDataBadge /></div>
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
                <Input id="title" placeholder="Incident title" />
              </div>
              <div>
                <Label htmlFor="severity">Severity</Label>
                <Select>
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
                <Textarea id="description" placeholder="Incident description" />
              </div>
              <Button className="w-full">Create Incident</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search incidents..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="investigating">Investigating</SelectItem>
                <SelectItem value="mitigating">Mitigating</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Incidents Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredIncidents.map((incident) => (
          <Card key={incident.id} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <Badge className={severityColors[incident.severity]}>
                  {incident.severity.toUpperCase()}
                </Badge>
                <Badge className={statusColors[incident.status]}>
                  {incident.status.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>
              <CardTitle className="text-lg leading-tight">
                {incident.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {incident.description}
                </p>
                
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    <span>{incident.alertCount} alerts</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{getTimeAgo(incident.updatedAt)}</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1 text-sm">
                    <User className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">{incident.assignee}</span>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {incident.id}
                  </Badge>
                </div>
                
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full"
                  onClick={() => setSelectedIncident(incident)}
                >
                  View Details
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Incident Detail Dialog */}
      <Dialog open={!!selectedIncident} onOpenChange={() => setSelectedIncident(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {selectedIncident && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <Badge className={severityColors[selectedIncident.severity]}>
                    {selectedIncident.severity.toUpperCase()}
                  </Badge>
                  <Badge className={statusColors[selectedIncident.status]}>
                    {selectedIncident.status.replace('_', ' ').toUpperCase()}
                  </Badge>
                </div>
                <DialogTitle className="text-xl">
                  {selectedIncident.title}
                </DialogTitle>
              </DialogHeader>
              
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label className="text-muted-foreground">Incident ID</Label>
                    <p className="font-medium">{selectedIncident.id}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Assignee</Label>
                    <p className="font-medium">{selectedIncident.assignee}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Created</Label>
                    <p className="font-medium">{formatTimestamp(selectedIncident.createdAt)}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Last Updated</Label>
                    <p className="font-medium">{formatTimestamp(selectedIncident.updatedAt)}</p>
                  </div>
                </div>
                
                <div>
                  <Label className="text-muted-foreground">Description</Label>
                  <p className="mt-1">{selectedIncident.description}</p>
                </div>
                
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <MessageSquare className="h-4 w-4" />
                    <Label>Activity Timeline ({selectedIncident.notes.length} notes)</Label>
                  </div>
                  <div className="space-y-3">
                    {selectedIncident.notes.map((note) => (
                      <div key={note.id} className="p-3 rounded-lg bg-muted/50 border">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium">{note.author}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatTimestamp(note.timestamp)}
                          </span>
                        </div>
                        <p className="text-sm">{note.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="flex gap-2">
                  <Button variant="outline" className="flex-1">
                    Add Note
                  </Button>
                  <Button variant="outline" className="flex-1">
                    Change Status
                  </Button>
                  <Button className="flex-1 bg-gradient-cyber">
                    Take Action
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