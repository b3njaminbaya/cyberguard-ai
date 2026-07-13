import { useState } from "react"
import { ThreatBadge, ThreatLevel } from "@/components/ThreatBadge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { LoadingState, ErrorState } from "@/components/QueryState"
import { AlertTriangle, Search, Eye, Clock, Sparkles, Loader2, RotateCw } from "lucide-react"
import { useThreats } from "@/hooks/useApi"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, ApiError, type ThreatDto } from "@/lib/api"
import { toast } from "@/hooks/use-toast"

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp)
  const diffMs = Date.now() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return "Just now"
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return date.toLocaleDateString()
}

function formatBytes(bytes: number) {
  if (!bytes) return '0 B'
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

export default function Threats() {
  const { data, isPending, isError, error } = useThreats(100)
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState("")
  const [severityFilter, setSeverityFilter] = useState<string>("all")
  const [protocolFilter, setProtocolFilter] = useState<string>("all")
  const [selectedThreat, setSelectedThreat] = useState<ThreatDto | null>(null)

  const triage = useMutation({
    mutationFn: ({ id, regenerate }: { id: string; regenerate?: boolean }) =>
      api.triageThreat(id, regenerate),
    onSuccess: (updated) => {
      setSelectedThreat(updated)
      queryClient.setQueryData<ThreatDto[]>(["threats", 100], (old) =>
        old?.map((t) => (t.id === updated.id ? updated : t))
      )
    },
    onError: (err: ApiError) =>
      toast({ title: "Triage failed", description: err.message, variant: "destructive" }),
  })

  if (isPending) return <LoadingState label="Loading threats…" />
  if (isError) return <ErrorState message={(error as Error).message} />

  const protocols = Array.from(new Set(data.map(t => t.protocol).filter(Boolean))) as string[]

  const filtered = data.filter((t) => {
    const q = searchTerm.toLowerCase()
    const matchesSearch =
      t.label.toLowerCase().includes(q) ||
      t.id.toLowerCase().includes(q) ||
      (t.source_ip ?? "").includes(q) ||
      (t.dest_ip ?? "").includes(q)
    const matchesSeverity = severityFilter === "all" || t.severity === severityFilter
    const matchesProtocol = protocolFilter === "all" || t.protocol === protocolFilter
    return matchesSearch && matchesSeverity && matchesProtocol
  })

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Threat Feed</h1>
          <p className="text-muted-foreground">
            {data.length} threats detected by the model out of the ingested event set
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by category, IP, or ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
              </SelectContent>
            </Select>
            <Select value={protocolFilter} onValueChange={setProtocolFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Protocol" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Protocols</SelectItem>
                {protocols.map(p => (
                  <SelectItem key={p} value={p}>{p.toUpperCase()}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {filtered.map((t) => (
          <Card key={t.id} className={`transition-all hover:shadow-md ${
            t.severity === 'critical' ? 'border-critical/30' :
            t.severity === 'high' ? 'border-high/30' : ''
          }`}>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-3">
                    <ThreatBadge level={t.severity as ThreatLevel} />
                    <Badge variant="secondary" className="text-xs">{t.protocol?.toUpperCase()}</Badge>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatTimestamp(t.created_at)}
                    </div>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">
                      {t.label} — traffic flagged by the anomaly detector
                    </p>
                    <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                      <span>Confidence: {(t.score * 100).toFixed(1)}%</span>
                      <span>Source: {t.source_ip}</span>
                      <span>Dest: {t.dest_ip}</span>
                      {t.bytes ? <span>Data: {formatBytes(t.bytes)}</span> : null}
                    </div>
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={() => setSelectedThreat(t)}>
                  <Eye className="h-4 w-4 mr-1" />
                  Details
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center">
            <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-lg font-medium">No threats found</p>
            <p className="text-muted-foreground">Try adjusting your filters or search terms</p>
          </CardContent>
        </Card>
      )}

      {selectedThreat && (
        <Card className="border-primary/50">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Threat {selectedThreat.id.slice(0, 8)}</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setSelectedThreat(null)}>Close</Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm space-y-1 font-mono">
              <p>category: {selectedThreat.label}</p>
              <p>severity: {selectedThreat.severity}</p>
              <p>confidence: {selectedThreat.score.toFixed(3)}</p>
              <p>source_ip: {selectedThreat.source_ip}</p>
              <p>dest_ip: {selectedThreat.dest_ip}</p>
              <p>protocol: {selectedThreat.protocol}</p>
              <p>event_id: {selectedThreat.event_id}</p>
              <p>detected_at: {selectedThreat.created_at}</p>
            </div>

            <div className="border-t pt-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  AI Triage Note
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={triage.isPending}
                  onClick={() => triage.mutate({ id: selectedThreat.id, regenerate: !!selectedThreat.summary })}
                >
                  {triage.isPending ? (
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  ) : selectedThreat.summary ? (
                    <RotateCw className="h-3 w-3 mr-1" />
                  ) : (
                    <Sparkles className="h-3 w-3 mr-1" />
                  )}
                  {triage.isPending ? "Thinking…" : selectedThreat.summary ? "Regenerate" : "Triage with AI"}
                </Button>
              </div>
              {triage.isPending && (
                <p className="text-xs text-muted-foreground">
                  Running locally via Ollama — first response can take up to a minute while the model loads.
                </p>
              )}
              {selectedThreat.summary && !triage.isPending && (
                <p className="text-sm bg-muted/50 rounded-md p-3 whitespace-pre-line">{selectedThreat.summary}</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
