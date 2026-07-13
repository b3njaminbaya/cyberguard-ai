import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { toast } from "@/hooks/use-toast"
import { Settings as SettingsIcon, Bell, Mail, Webhook, Shield, Database, Cpu, TestTube2, AlertTriangle, Lock } from "lucide-react"
import { DemoDataBadge } from "@/components/DemoDataBadge"
import { LoadingState, ErrorState } from "@/components/QueryState"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api, ApiError, type NotificationSettingsInput } from "@/lib/api"
import { useAuth } from "@/lib/AuthContext"

function NotificationsTab() {
  const { user } = useAuth()
  const isAdmin = user?.role === "Admin"
  const queryClient = useQueryClient()
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["notification-settings"],
    queryFn: api.notificationSettings,
  })
  const [form, setForm] = useState<NotificationSettingsInput | null>(null)

  useEffect(() => {
    if (data) setForm(data)
  }, [data])

  const save = useMutation({
    mutationFn: (payload: NotificationSettingsInput) => api.saveNotificationSettings(payload),
    onSuccess: (saved) => {
      queryClient.setQueryData(["notification-settings"], saved)
      toast({ title: "Settings saved", description: "Notification configuration updated." })
    },
    onError: (err: ApiError) => toast({ title: "Save failed", description: err.message, variant: "destructive" }),
  })

  const runTest = useMutation({
    mutationFn: (channel: "slack" | "email" | "webhook") =>
      channel === "slack" ? api.testSlack() : channel === "email" ? api.testEmail() : api.testWebhook(),
    onSuccess: (_res, channel) =>
      toast({ title: "Test sent", description: `Check your ${channel} destination — a real message was just sent.` }),
    onError: (err: ApiError) => toast({ title: "Test failed", description: err.message, variant: "destructive" }),
  })

  if (isPending || !form) return <LoadingState label="Loading notification settings…" />
  if (isError) return <ErrorState message={(error as Error).message} />

  const set = <K extends keyof NotificationSettingsInput>(key: K, value: NotificationSettingsInput[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Alert Notifications
          </span>
          <Button size="sm" disabled={!isAdmin || save.isPending} onClick={() => save.mutate(form)}>
            {save.isPending ? "Saving…" : "Save Changes"}
          </Button>
        </CardTitle>
        <CardDescription>
          Real delivery — Slack via Incoming Webhook, email via SMTP, and a generic signed webhook. Saving and
          testing requires the Admin role.
        </CardDescription>
        {!isAdmin && (
          <div className="flex items-center gap-2 text-sm text-warning bg-warning/10 border border-warning/30 rounded-md px-3 py-2 mt-2">
            <Lock className="h-4 w-4 shrink-0" />
            You're signed in as "{user?.role ?? "unknown"}" — an Admin needs to promote your account before you can change these settings.
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label className="text-base">Enable Notifications</Label>
            <p className="text-sm text-muted-foreground">Master toggle for all alert notifications</p>
          </div>
          <Switch
            disabled={!isAdmin}
            checked={form.notifications_enabled}
            onCheckedChange={(v) => set("notifications_enabled", v)}
          />
        </div>

        <Separator />

        {/* Email Notifications */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base flex items-center gap-2">
                <Mail className="h-4 w-4" />
                Email Alerts
              </Label>
              <p className="text-sm text-muted-foreground">Sent via the SMTP account configured on the backend</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={!isAdmin || runTest.isPending} onClick={() => runTest.mutate("email")}>
                <TestTube2 className="h-3 w-3 mr-1" />
                Test
              </Button>
              <Switch disabled={!isAdmin} checked={form.email_enabled} onCheckedChange={(v) => set("email_enabled", v)} />
            </div>
          </div>

          {form.email_enabled && (
            <div className="ml-6 space-y-4 p-4 border rounded-lg">
              <div className="space-y-2">
                <Label htmlFor="email-recipients">Recipients (comma-separated)</Label>
                <Textarea
                  id="email-recipients"
                  placeholder="admin@company.com, security@company.com"
                  rows={2}
                  disabled={!isAdmin}
                  value={form.email_recipients}
                  onChange={(e) => set("email_recipients", e.target.value)}
                />
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Slack Notifications */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base">Slack Integration</Label>
              <p className="text-sm text-muted-foreground">Send alerts via an Incoming Webhook</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={!isAdmin || runTest.isPending} onClick={() => runTest.mutate("slack")}>
                <TestTube2 className="h-3 w-3 mr-1" />
                Test
              </Button>
              <Switch disabled={!isAdmin} checked={form.slack_enabled} onCheckedChange={(v) => set("slack_enabled", v)} />
            </div>
          </div>

          {form.slack_enabled && (
            <div className="ml-6 space-y-4 p-4 border rounded-lg">
              <div className="space-y-2">
                <Label htmlFor="slack-webhook">Webhook URL</Label>
                <Input
                  id="slack-webhook"
                  placeholder="https://hooks.slack.com/services/..."
                  type="password"
                  disabled={!isAdmin}
                  value={form.slack_webhook_url ?? ""}
                  onChange={(e) => set("slack_webhook_url", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="slack-channel">Channel (informational — set at webhook creation time)</Label>
                <Input
                  id="slack-channel"
                  placeholder="#security-alerts"
                  disabled={!isAdmin}
                  value={form.slack_channel ?? ""}
                  onChange={(e) => set("slack_channel", e.target.value)}
                />
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Webhook Notifications */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base flex items-center gap-2">
                <Webhook className="h-4 w-4" />
                Custom Webhook
              </Label>
              <p className="text-sm text-muted-foreground">POSTs a JSON payload, HMAC-SHA256 signed if a secret is set</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={!isAdmin || runTest.isPending} onClick={() => runTest.mutate("webhook")}>
                <TestTube2 className="h-3 w-3 mr-1" />
                Test
              </Button>
              <Switch disabled={!isAdmin} checked={form.webhook_enabled} onCheckedChange={(v) => set("webhook_enabled", v)} />
            </div>
          </div>

          {form.webhook_enabled && (
            <div className="ml-6 space-y-4 p-4 border rounded-lg">
              <div className="space-y-2">
                <Label htmlFor="webhook-url">Webhook URL</Label>
                <Input
                  id="webhook-url"
                  placeholder="https://api.company.com/alerts"
                  disabled={!isAdmin}
                  value={form.webhook_url ?? ""}
                  onChange={(e) => set("webhook_url", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="webhook-secret">Secret Key (optional — signs the payload)</Label>
                <Input
                  id="webhook-secret"
                  type="password"
                  placeholder="webhook_secret_key"
                  disabled={!isAdmin}
                  value={form.webhook_secret ?? ""}
                  onChange={(e) => set("webhook_secret", e.target.value)}
                />
              </div>
            </div>
          )}
        </div>

        <Separator />

        <div className="space-y-4">
          <Label className="text-base">Alert Severity Thresholds</Label>
          <p className="text-sm text-muted-foreground -mt-2">
            Only these severities trigger delivery. No "low" tier — the model doesn't produce one.
          </p>
          <div className="grid grid-cols-3 gap-4 max-w-sm">
            <div className="space-y-2">
              <Label className="text-sm text-critical">Critical</Label>
              <Switch disabled={!isAdmin} checked={form.alert_on_critical} onCheckedChange={(v) => set("alert_on_critical", v)} />
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-warning">High</Label>
              <Switch disabled={!isAdmin} checked={form.alert_on_high} onCheckedChange={(v) => set("alert_on_high", v)} />
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-accent">Medium</Label>
              <Switch disabled={!isAdmin} checked={form.alert_on_medium} onCheckedChange={(v) => set("alert_on_medium", v)} />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Settings() {
  const [mfaRequired, setMfaRequired] = useState(false)
  const [autoRetrain, setAutoRetrain] = useState(true)

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground">Configure system preferences and integrations</p>
        </div>
      </div>

      <Tabs defaultValue="notifications" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="models">AI Models</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <DemoDataBadge />
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SettingsIcon className="h-5 w-5" />
                Organization Settings
              </CardTitle>
              <CardDescription>
                Configure basic organization information and preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="org-name">Organization Name</Label>
                  <Input id="org-name" defaultValue="CyberGuard Security" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="contact-email">Contact Email</Label>
                  <Input id="contact-email" type="email" defaultValue="admin@cyberguard.com" />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="timezone">Default Timezone</Label>
                <Select defaultValue="utc">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="utc">UTC</SelectItem>
                    <SelectItem value="est">Eastern Time</SelectItem>
                    <SelectItem value="pst">Pacific Time</SelectItem>
                    <SelectItem value="cet">Central European Time</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="retention">Log Retention Period</Label>
                <Select defaultValue="90">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="30">30 days</SelectItem>
                    <SelectItem value="90">90 days</SelectItem>
                    <SelectItem value="180">180 days</SelectItem>
                    <SelectItem value="365">1 year</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">Dark Mode</Label>
                  <p className="text-sm text-muted-foreground">Use dark theme across the application</p>
                </div>
                <Switch defaultChecked />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">Real-time Updates</Label>
                  <p className="text-sm text-muted-foreground">Enable live data updates in dashboards</p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <NotificationsTab />
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <DemoDataBadge />
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Security Settings
              </CardTitle>
              <CardDescription>
                Configure authentication and access control settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">Require Multi-Factor Authentication</Label>
                  <p className="text-sm text-muted-foreground">Enforce MFA for all user accounts</p>
                </div>
                <Switch checked={mfaRequired} onCheckedChange={setMfaRequired} />
              </div>

              <Separator />

              <div className="space-y-4">
                <Label className="text-base">Session Management</Label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="session-timeout">Session Timeout (minutes)</Label>
                    <Select defaultValue="30">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="15">15 minutes</SelectItem>
                        <SelectItem value="30">30 minutes</SelectItem>
                        <SelectItem value="60">1 hour</SelectItem>
                        <SelectItem value="240">4 hours</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="max-sessions">Max Concurrent Sessions</Label>
                    <Select defaultValue="3">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1 session</SelectItem>
                        <SelectItem value="3">3 sessions</SelectItem>
                        <SelectItem value="5">5 sessions</SelectItem>
                        <SelectItem value="-1">Unlimited</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <Label className="text-base">Password Policy</Label>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Minimum length: 8 characters</span>
                    <Badge variant="outline">Required</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Require uppercase letters</span>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Require numbers</span>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Require special characters</span>
                    <Switch />
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <Label className="text-base">API Security</Label>
                <div className="space-y-2">
                  <Label htmlFor="api-rate-limit">Rate Limit (requests per minute)</Label>
                  <Input id="api-rate-limit" defaultValue="1000" type="number" />
                </div>
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-base">Enable API Key Rotation</Label>
                    <p className="text-sm text-muted-foreground">Automatically rotate API keys every 90 days</p>
                  </div>
                  <Switch />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="models" className="space-y-6">
          <DemoDataBadge />
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Cpu className="h-5 w-5" />
                AI Model Configuration
              </CardTitle>
              <CardDescription>
                Configure AI model settings and training parameters
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">Automatic Model Retraining</Label>
                  <p className="text-sm text-muted-foreground">Retrain models when performance degrades</p>
                </div>
                <Switch checked={autoRetrain} onCheckedChange={setAutoRetrain} />
              </div>

              <Separator />

              <div className="space-y-4">
                <Label className="text-base">Training Parameters</Label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="batch-size">Batch Size</Label>
                    <Select defaultValue="32">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="16">16</SelectItem>
                        <SelectItem value="32">32</SelectItem>
                        <SelectItem value="64">64</SelectItem>
                        <SelectItem value="128">128</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="learning-rate">Learning Rate</Label>
                    <Input id="learning-rate" defaultValue="0.001" step="0.0001" type="number" />
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <Label className="text-base">Model Performance Thresholds</Label>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Minimum Accuracy</span>
                    <div className="flex items-center gap-2">
                      <Input className="w-20" defaultValue="0.85" step="0.01" type="number" />
                      <span className="text-sm text-muted-foreground">85%</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Maximum False Positive Rate</span>
                    <div className="flex items-center gap-2">
                      <Input className="w-20" defaultValue="0.05" step="0.01" type="number" />
                      <span className="text-sm text-muted-foreground">5%</span>
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <Label className="text-base">Data Drift Detection</Label>
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-base">Enable Drift Monitoring</Label>
                    <p className="text-sm text-muted-foreground">Monitor for changes in data distribution</p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="drift-threshold">Drift Alert Threshold</Label>
                  <Select defaultValue="0.1">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0.05">Low (5%)</SelectItem>
                      <SelectItem value="0.1">Medium (10%)</SelectItem>
                      <SelectItem value="0.2">High (20%)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="system" className="space-y-6">
          <DemoDataBadge />
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                System Configuration
              </CardTitle>
              <CardDescription>
                Configure system resources and performance settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <Label className="text-base">Resource Allocation</Label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="cpu-limit">CPU Limit (%)</Label>
                    <Input id="cpu-limit" defaultValue="80" type="number" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="memory-limit">Memory Limit (GB)</Label>
                    <Input id="memory-limit" defaultValue="16" type="number" />
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <Label className="text-base">Database Settings</Label>
                <div className="space-y-2">
                  <Label htmlFor="db-pool-size">Connection Pool Size</Label>
                  <Select defaultValue="20">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10 connections</SelectItem>
                      <SelectItem value="20">20 connections</SelectItem>
                      <SelectItem value="50">50 connections</SelectItem>
                      <SelectItem value="100">100 connections</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-base">Enable Query Caching</Label>
                    <p className="text-sm text-muted-foreground">Cache frequently accessed queries</p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <Label className="text-base">Monitoring & Logging</Label>
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-base">Enable Metrics Collection</Label>
                    <p className="text-sm text-muted-foreground">Collect system performance metrics</p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="log-level">System Log Level</Label>
                  <Select defaultValue="info">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="debug">Debug</SelectItem>
                      <SelectItem value="info">Info</SelectItem>
                      <SelectItem value="warn">Warning</SelectItem>
                      <SelectItem value="error">Error</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Separator />

              <div className="p-4 border border-warning/30 rounded-lg bg-warning/5">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-warning mt-0.5" />
                  <div>
                    <h4 className="font-medium text-warning">Danger Zone</h4>
                    <p className="text-sm text-muted-foreground mt-1">
                      These actions are irreversible and can cause data loss.
                    </p>
                    <div className="flex gap-2 mt-4">
                      <Button variant="outline" size="sm">
                        Reset Configuration
                      </Button>
                      <Button variant="destructive" size="sm">
                        Factory Reset
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
