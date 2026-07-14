import { MetricCard } from "@/components/MetricCard"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { LoadingState, ErrorState } from "@/components/QueryState"
import { Brain, TrendingUp, Target, AlertTriangle, Gauge } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useModelMetrics } from "@/hooks/useApi"

export default function Models() {
  const { data, isPending, isError, error } = useModelMetrics()

  if (isPending) return <LoadingState label="Loading model metrics…" />
  if (isError) return <ErrorState message={(error as Error).message} />

  if (!data.trained) {
    return (
      <div className="space-y-6 p-6">
        <h1 className="text-3xl font-bold tracking-tight">AI Models</h1>
        <Card>
          <CardContent className="pt-6 text-center space-y-2">
            <AlertTriangle className="h-10 w-10 mx-auto text-muted-foreground" />
            <p className="font-medium">No model trained yet</p>
            <p className="text-sm text-muted-foreground font-mono">cd backend && python -m detection.train</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const perClassData = Object.entries(data.per_class)
    .filter(([name]) => name !== "accuracy")
    .map(([name, m]) => ({
      name,
      precision: Math.round(m.precision * 100),
      recall: Math.round(m.recall * 100),
      f1: Math.round(m["f1-score"] * 100),
      support: m.support,
    }))
    .sort((a, b) => b.support - a.support)

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Models</h1>
          <p className="text-muted-foreground">Detection model trained on the real UNSW-NB15 dataset — no synthetic metrics</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Accuracy" value={`${(data.accuracy! * 100).toFixed(1)}%`} icon={Target} variant="success" />
        <MetricCard title="Weighted F1" value={(data.weighted_f1! * 100).toFixed(1) + '%'} icon={TrendingUp} variant="default" />
        <MetricCard title="Macro F1" value={(data.macro_f1! * 100).toFixed(1) + '%'} icon={Brain} variant="default"
          change={{ value: "lower — rare classes are harder", type: "neutral" }} />
        <MetricCard title="Classes" value={perClassData.length} icon={AlertTriangle} variant="warning" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Model Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between border-b pb-2"><span className="text-muted-foreground">Algorithm</span><span>RandomForestClassifier (scikit-learn), 200 trees</span></div>
          <div className="flex justify-between border-b pb-2"><span className="text-muted-foreground">Training data</span><span>UNSW-NB15, 175,341 labeled flow records</span></div>
          <div className="flex justify-between border-b pb-2"><span className="text-muted-foreground">Target</span><span>Multi-class attack category (10 classes incl. Normal)</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Last trained</span><span>{new Date(data.trained_at!).toLocaleString()}</span></div>
        </CardContent>
      </Card>

      {data.feature_importance.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-5 w-5 text-primary" />
              What The Model Actually Looks At
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Real `feature_importances_` from the trained RandomForest, aggregated back from 194 one-hot columns to
              the original 39 fields — not asserted, computed.
            </p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={340}>
              <BarChart
                data={[...data.feature_importance].reverse()}
                layout="vertical"
                margin={{ left: 24 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis type="number" stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                <YAxis type="category" dataKey="feature" stroke="hsl(var(--muted-foreground))" width={110} tick={{ fontFamily: "monospace", fontSize: 12 }} />
                <Tooltip
                  formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px' }}
                />
                <Bar dataKey="importance" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            Per-Category Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={perClassData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" angle={-20} textAnchor="end" height={60} />
              <YAxis stroke="hsl(var(--muted-foreground))" domain={[0, 100]} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px' }} />
              <Bar dataKey="precision" fill="hsl(var(--primary))" name="Precision %" />
              <Bar dataKey="recall" fill="hsl(var(--warning))" name="Recall %" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Per-Category Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Category</TableHead>
                <TableHead>Precision</TableHead>
                <TableHead>Recall</TableHead>
                <TableHead>F1</TableHead>
                <TableHead>Test samples</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {perClassData.map((c) => (
                <TableRow key={c.name}>
                  <TableCell className="font-medium">
                    {c.name}
                    {c.name === "Normal" && <Badge variant="outline" className="ml-2 text-xs">not a threat</Badge>}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress value={c.precision} className="w-24" />
                      <span className="text-sm">{c.precision}%</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress value={c.recall} className="w-24" />
                      <span className="text-sm">{c.recall}%</span>
                    </div>
                  </TableCell>
                  <TableCell>{c.f1}%</TableCell>
                  <TableCell className="text-muted-foreground">{c.support.toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
