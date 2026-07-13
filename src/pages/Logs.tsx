import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { MetricCard } from "@/components/MetricCard"
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { FileText, AlertCircle, TrendingUp, Search, Filter, Download, RefreshCw, Calendar } from "lucide-react"
import { DemoDataBadge } from "@/components/DemoDataBadge"

const mockLogTrends = [
  { time: "00:00", errors: 12, warnings: 45, info: 234, debug: 567 },
  { time: "04:00", errors: 8, warnings: 38, info: 189, debug: 432 },
  { time: "08:00", errors: 23, warnings: 67, info: 345, debug: 678 },
  { time: "12:00", errors: 34, warnings: 89, info: 456, debug: 789 },
  { time: "16:00", errors: 19, warnings: 56, info: 298, debug: 634 },
  { time: "20:00", errors: 15, warnings: 42, info: 267, debug: 523 },
]

const mockLogSources = [
  { source: "web-server", logs: 12456, errors: 34, warnings: 89, lastSeen: "2 min ago" },
  { source: "database", logs: 8934, errors: 12, warnings: 45, lastSeen: "1 min ago" },
  { source: "auth-service", logs: 6723, errors: 67, warnings: 123, lastSeen: "3 min ago" },
  { source: "api-gateway", logs: 15234, errors: 23, warnings: 78, lastSeen: "1 min ago" },
  { source: "load-balancer", logs: 4567, errors: 5, warnings: 12, lastSeen: "2 min ago" },
]

const mockRecentLogs = [
  {
    timestamp: "2024-01-20 14:23:45",
    level: "ERROR",
    source: "web-server-01",
    message: "Failed to connect to database: Connection timeout after 30s",
    details: "Database connection pool exhausted. Max connections: 100, Active: 100"
  },
  {
    timestamp: "2024-01-20 14:23:42",
    level: "WARN",
    source: "auth-service",
    message: "Multiple failed login attempts detected for user admin",
    details: "IP: 203.0.113.45, Attempts: 5, Time window: 2 minutes"
  },
  {
    timestamp: "2024-01-20 14:23:38",
    level: "ERROR",
    source: "api-gateway",
    message: "Rate limit exceeded for API key: ak_1234567890",
    details: "Current rate: 1500 req/min, Limit: 1000 req/min"
  },
  {
    timestamp: "2024-01-20 14:23:35",
    level: "INFO",
    source: "load-balancer",
    message: "Health check passed for backend server 192.168.1.100",
    details: "Response time: 45ms, Status: 200 OK"
  },
  {
    timestamp: "2024-01-20 14:23:30",
    level: "WARN",
    source: "database",
    message: "Slow query detected: execution time 15.2s",
    details: "Query: SELECT * FROM users WHERE created_at > '2024-01-01'"
  },
]

const mockLogTemplates = [
  { template: "Failed authentication attempt", count: 1247, trend: "+15%", severity: "high" },
  { template: "Database connection timeout", count: 89, trend: "+45%", severity: "critical" },
  { template: "API rate limit exceeded", count: 567, trend: "+8%", severity: "medium" },
  { template: "SSL certificate expiring", count: 12, trend: "0%", severity: "medium" },
  { template: "Disk space warning", count: 34, trend: "-12%", severity: "low" },
]

const getLevelColor = (level: string) => {
  switch (level.toLowerCase()) {
    case "error": return "text-critical"
    case "warn": case "warning": return "text-warning"
    case "info": return "text-primary"
    case "debug": return "text-muted-foreground"
    default: return "text-foreground"
  }
}

const getLevelBadgeVariant = (level: string) => {
  switch (level.toLowerCase()) {
    case "error": return "destructive"
    case "warn": case "warning": return "secondary"
    case "info": return "default"
    case "debug": return "outline"
    default: return "outline"
  }
}

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case "critical": return "text-critical"
    case "high": return "text-warning"
    case "medium": return "text-accent"
    case "low": return "text-success"
    default: return "text-muted-foreground"
  }
}

export default function Logs() {
  const [timeRange, setTimeRange] = useState("24h")
  const [logLevel, setLogLevel] = useState("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedSource, setSelectedSource] = useState("all")

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Log Analytics</h1>
          <p className="text-muted-foreground">Centralized log analysis and anomaly detection</p>
          <div className="mt-2"><DemoDataBadge /></div>
        </div>
        <div className="flex items-center gap-4">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last Hour</SelectItem>
              <SelectItem value="24h">Last 24h</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon">
            <Calendar className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Log Events"
          value="2.4M"
          change={{ value: "+8% from yesterday", type: "increase" }}
          icon={FileText}
          variant="default"
        />
        <MetricCard
          title="Error Rate"
          value="0.12%"
          change={{ value: "+0.03% from yesterday", type: "increase" }}
          icon={AlertCircle}
          variant="warning"
        />
        <MetricCard
          title="Active Sources"
          value="47"
          change={{ value: "+2 new sources", type: "increase" }}
          icon={TrendingUp}
          variant="success"
        />
        <MetricCard
          title="Anomalies Found"
          value="18"
          change={{ value: "+6 in last hour", type: "increase" }}
          icon={AlertCircle}
          variant="critical"
        />
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="search">Search & Filter</TabsTrigger>
          <TabsTrigger value="templates">Log Templates</TabsTrigger>
          <TabsTrigger value="anomalies">Anomaly Detection</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Log Volume Trends (24h)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={mockLogTrends}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="time" className="text-muted-foreground" />
                    <YAxis className="text-muted-foreground" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--card))", 
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px"
                      }} 
                    />
                    <Legend />
                    <Line type="monotone" dataKey="errors" stroke="hsl(var(--critical))" name="Errors" strokeWidth={2} />
                    <Line type="monotone" dataKey="warnings" stroke="hsl(var(--warning))" name="Warnings" strokeWidth={2} />
                    <Line type="monotone" dataKey="info" stroke="hsl(var(--primary))" name="Info" strokeWidth={2} />
                    <Line type="monotone" dataKey="debug" stroke="hsl(var(--muted-foreground))" name="Debug" strokeWidth={1} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Log Levels Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={mockLogTrends}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="time" className="text-muted-foreground" />
                    <YAxis className="text-muted-foreground" />
                    <Tooltip />
                    <Bar dataKey="errors" fill="hsl(var(--critical))" name="Errors" />
                    <Bar dataKey="warnings" fill="hsl(var(--warning))" name="Warnings" />
                    <Bar dataKey="info" fill="hsl(var(--primary))" name="Info" />
                    <Bar dataKey="debug" fill="hsl(var(--muted-foreground))" name="Debug" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Log Sources Status</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Source</TableHead>
                    <TableHead>Total Logs</TableHead>
                    <TableHead>Errors</TableHead>
                    <TableHead>Warnings</TableHead>
                    <TableHead>Last Seen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockLogSources.map((source, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{source.source}</TableCell>
                      <TableCell>{source.logs.toLocaleString()}</TableCell>
                      <TableCell className="text-critical">{source.errors}</TableCell>
                      <TableCell className="text-warning">{source.warnings}</TableCell>
                      <TableCell className="text-muted-foreground">{source.lastSeen}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="search" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Search & Filter Logs</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input 
                    placeholder="Search logs..." 
                    className="pl-8"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <Select value={logLevel} onValueChange={setLogLevel}>
                  <SelectTrigger>
                    <SelectValue placeholder="Log Level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Levels</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                    <SelectItem value="warn">Warning</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="debug">Debug</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={selectedSource} onValueChange={setSelectedSource}>
                  <SelectTrigger>
                    <SelectValue placeholder="Source" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Sources</SelectItem>
                    {mockLogSources.map(source => (
                      <SelectItem key={source.source} value={source.source}>
                        {source.source}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="outline" className="flex items-center gap-2">
                  <Download className="h-4 w-4" />
                  Export
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Log Events</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockRecentLogs.map((log, index) => (
                  <div key={index} className="border rounded-lg p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant={getLevelBadgeVariant(log.level)} className={getLevelColor(log.level)}>
                          {log.level}
                        </Badge>
                        <span className="font-medium">{log.source}</span>
                        <span className="text-sm text-muted-foreground font-mono">{log.timestamp}</span>
                      </div>
                    </div>
                    <p className="text-sm">{log.message}</p>
                    {log.details && (
                      <p className="text-xs text-muted-foreground bg-muted p-2 rounded font-mono">
                        {log.details}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="templates" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Log Template Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Template</TableHead>
                    <TableHead>Count (24h)</TableHead>
                    <TableHead>Trend</TableHead>
                    <TableHead>Severity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockLogTemplates.map((template, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{template.template}</TableCell>
                      <TableCell>{template.count.toLocaleString()}</TableCell>
                      <TableCell className={template.trend.startsWith('+') ? 'text-warning' : template.trend.startsWith('-') ? 'text-success' : 'text-muted-foreground'}>
                        {template.trend}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={getSeverityColor(template.severity)}>
                          {template.severity.toUpperCase()}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="anomalies" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-warning" />
                Anomaly Detection Results
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-center h-96">
              <div className="text-center space-y-4">
                <AlertCircle className="h-16 w-16 mx-auto text-muted-foreground" />
                <div>
                  <p className="text-lg font-medium">AI-Powered Log Anomaly Detection</p>
                  <p className="text-muted-foreground">Advanced pattern recognition for unusual log behavior</p>
                </div>
                <Button>Configure Anomaly Detection</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}