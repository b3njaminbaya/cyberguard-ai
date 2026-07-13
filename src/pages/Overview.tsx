import { MetricCard } from "@/components/MetricCard"
import { ThreatBadge, ThreatLevel } from "@/components/ThreatBadge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LoadingState, ErrorState } from "@/components/QueryState"
import { AlertTriangle, Shield, Activity, Brain, Network } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { useSummary, useThreats, useModelMetrics } from "@/hooks/useApi"

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
}

export default function Overview() {
  const summary = useSummary()
  const threats = useThreats(6)
  const modelMetrics = useModelMetrics()

  if (summary.isPending || threats.isPending) return <LoadingState label="Loading security overview…" />
  if (summary.isError) return <ErrorState message={(summary.error as Error).message} />

  const s = summary.data!
  const severityChartData = Object.entries(s.by_severity)
    .filter(([, count]) => count > 0)
    .map(([severity, count]) => ({ severity, count, color: SEVERITY_COLORS[severity] ?? '#94a3b8' }))

  const categoryChartData = Object.entries(s.by_category)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Security Overview</h1>
          <p className="text-muted-foreground">Live detection results from the trained anomaly-detection model</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <div className="h-2 w-2 rounded-full bg-success animate-pulse"></div>
            <span>Connected to API</span>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Events Ingested"
          value={s.total_events.toLocaleString()}
          icon={Network}
          variant="default"
        />
        <MetricCard
          title="Threats Detected"
          value={s.total_threats.toLocaleString()}
          change={{ value: `${s.total_events ? Math.round((s.total_threats / s.total_events) * 100) : 0}% of ingested events`, type: "neutral" }}
          icon={AlertTriangle}
          variant="critical"
        />
        <MetricCard
          title="Critical Severity"
          value={s.by_severity.critical}
          icon={Shield}
          variant="warning"
        />
        <MetricCard
          title="Model Accuracy"
          value={modelMetrics.data?.trained ? `${(modelMetrics.data.accuracy! * 100).toFixed(1)}%` : "—"}
          change={{ value: "RandomForest on UNSW-NB15", type: "neutral" }}
          icon={Brain}
          variant="default"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Threats by Severity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={severityChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="severity" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {severityChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Threat Categories</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={categoryChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  dataKey="value"
                >
                  {categoryChartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={`hsl(${(index * 57) % 360} 70% 55%)`} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-2 gap-2 mt-4">
              {categoryChartData.map((c, index) => (
                <div key={index} className="flex items-center gap-2 text-sm">
                  <div
                    className="h-3 w-3 rounded-sm"
                    style={{ backgroundColor: `hsl(${(index * 57) % 360} 70% 55%)` }}
                  />
                  <span className="text-muted-foreground">{c.name}</span>
                  <span className="font-medium">{c.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-primary" />
            Most Recent Threats
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {threats.data!.map((t) => (
              <div key={t.id} className="flex items-center justify-between p-3 rounded-lg border bg-card/50">
                <div className="flex items-start gap-3">
                  <ThreatBadge level={t.severity as ThreatLevel} />
                  <div>
                    <p className="text-sm font-medium">
                      {t.label} detected — {t.source_ip} → {t.dest_ip} ({t.protocol})
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(t.created_at).toLocaleString()} · confidence {(t.score * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {threats.data!.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-6">
                No threats yet — run <code className="font-mono">python scripts/seed_demo_data.py</code> in backend/.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
