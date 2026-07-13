import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { MetricCard } from "@/components/MetricCard"
import { Users as UsersIcon, UserPlus, Shield, Key, Settings, Search, Filter, MoreHorizontal, Edit, Trash2, UserX } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { DemoDataBadge } from "@/components/DemoDataBadge"

const mockUsers = [
  {
    id: 1,
    name: "John Doe",
    email: "john.doe@company.com",
    role: "Admin",
    status: "active",
    lastLogin: "2024-01-20 14:30",
    avatar: "/api/placeholder/32/32",
    mfaEnabled: true,
    apiKeyCount: 3,
    department: "Security"
  },
  {
    id: 2,
    name: "Sarah Wilson",
    email: "sarah.wilson@company.com",
    role: "SecurityAnalyst",
    status: "active",
    lastLogin: "2024-01-20 13:45",
    avatar: "/api/placeholder/32/32",
    mfaEnabled: true,
    apiKeyCount: 1,
    department: "Security"
  },
  {
    id: 3,
    name: "Mike Johnson",
    email: "mike.johnson@company.com",
    role: "User",
    status: "active",
    lastLogin: "2024-01-20 09:15",
    avatar: "/api/placeholder/32/32",
    mfaEnabled: false,
    apiKeyCount: 0,
    department: "IT Operations"
  },
  {
    id: 4,
    name: "Emily Chen",
    email: "emily.chen@company.com",
    role: "SecurityAnalyst",
    status: "inactive",
    lastLogin: "2024-01-18 16:20",
    avatar: "/api/placeholder/32/32",
    mfaEnabled: true,
    apiKeyCount: 2,
    department: "Security"
  },
  {
    id: 5,
    name: "David Brown",
    email: "david.brown@company.com",
    role: "User",
    status: "suspended",
    lastLogin: "2024-01-15 11:30",
    avatar: "/api/placeholder/32/32",
    mfaEnabled: false,
    apiKeyCount: 0,
    department: "Development"
  },
]

const mockApiKeys = [
  {
    id: 1,
    name: "Production Ingestion",
    key: "ak_prod_1234567890",
    userId: 1,
    userName: "John Doe",
    created: "2024-01-10",
    lastUsed: "2024-01-20 14:25",
    usage: "2.4M requests",
    status: "active"
  },
  {
    id: 2,
    name: "Dev Environment",
    key: "ak_dev_abcdefghij",
    userId: 2,
    userName: "Sarah Wilson",
    created: "2024-01-15",
    lastUsed: "2024-01-20 12:30",
    usage: "456K requests",
    status: "active"
  },
  {
    id: 3,
    name: "Test Integration",
    key: "ak_test_xyz9876543",
    userId: 1,
    userName: "John Doe",
    created: "2024-01-18",
    lastUsed: "2024-01-19 18:45",
    usage: "23K requests",
    status: "active"
  },
]

const getRoleColor = (role: string) => {
  switch (role) {
    case "Admin": return "text-critical"
    case "SecurityAnalyst": return "text-warning"
    case "User": return "text-primary"
    default: return "text-muted-foreground"
  }
}

const getRoleBadgeVariant = (role: string) => {
  switch (role) {
    case "Admin": return "destructive"
    case "SecurityAnalyst": return "secondary"
    case "User": return "outline"
    default: return "outline"
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case "active": return "text-success"
    case "inactive": return "text-muted-foreground"
    case "suspended": return "text-critical"
    default: return "text-muted-foreground"
  }
}

const getStatusBadgeVariant = (status: string) => {
  switch (status) {
    case "active": return "default"
    case "inactive": return "secondary"
    case "suspended": return "destructive"
    default: return "outline"
  }
}

export default function Users() {
  const [searchQuery, setSearchQuery] = useState("")
  const [roleFilter, setRoleFilter] = useState("all")
  const [statusFilter, setStatusFilter] = useState("all")
  const [isCreateUserOpen, setIsCreateUserOpen] = useState(false)
  const [isCreateApiKeyOpen, setIsCreateApiKeyOpen] = useState(false)

  const filteredUsers = mockUsers.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesRole = roleFilter === "all" || user.role === roleFilter
    const matchesStatus = statusFilter === "all" || user.status === statusFilter
    return matchesSearch && matchesRole && matchesStatus
  })

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">User Management</h1>
          <p className="text-muted-foreground">Manage users, roles, and API access</p>
          <div className="mt-2"><DemoDataBadge /></div>
        </div>
        <div className="flex items-center gap-4">
          <Dialog open={isCreateApiKeyOpen} onOpenChange={setIsCreateApiKeyOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="flex items-center gap-2">
                <Key className="h-4 w-4" />
                New API Key
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create API Key</DialogTitle>
                <DialogDescription>
                  Generate a new API key for ingestion or integration purposes.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="api-key-name">Key Name</Label>
                  <Input id="api-key-name" placeholder="Production Ingestion Key" />
                </div>
                <div>
                  <Label htmlFor="api-key-user">Assign to User</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select user" />
                    </SelectTrigger>
                    <SelectContent>
                      {mockUsers.filter(u => u.status === 'active').map(user => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          {user.name} ({user.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsCreateApiKeyOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={() => setIsCreateApiKeyOpen(false)}>
                  Generate Key
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Dialog open={isCreateUserOpen} onOpenChange={setIsCreateUserOpen}>
            <DialogTrigger asChild>
              <Button className="flex items-center gap-2">
                <UserPlus className="h-4 w-4" />
                Add User
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New User</DialogTitle>
                <DialogDescription>
                  Create a new user account with appropriate permissions.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="first-name">First Name</Label>
                    <Input id="first-name" placeholder="John" />
                  </div>
                  <div>
                    <Label htmlFor="last-name">Last Name</Label>
                    <Input id="last-name" placeholder="Doe" />
                  </div>
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" placeholder="john.doe@company.com" />
                </div>
                <div>
                  <Label htmlFor="role">Role</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="User">User</SelectItem>
                      <SelectItem value="SecurityAnalyst">Security Analyst</SelectItem>
                      <SelectItem value="Admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="department">Department</Label>
                  <Input id="department" placeholder="Security" />
                </div>
                <div className="flex items-center space-x-2">
                  <Switch id="require-mfa" />
                  <Label htmlFor="require-mfa">Require MFA</Label>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsCreateUserOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={() => setIsCreateUserOpen(false)}>
                  Create User
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Users"
          value={mockUsers.length.toString()}
          change={{ value: "+2 this month", type: "increase" }}
          icon={UsersIcon}
          variant="default"
        />
        <MetricCard
          title="Active Users"
          value={mockUsers.filter(u => u.status === 'active').length.toString()}
          change={{ value: "85% active rate", type: "neutral" }}
          icon={Shield}
          variant="success"
        />
        <MetricCard
          title="API Keys"
          value={mockApiKeys.length.toString()}
          change={{ value: "+1 this week", type: "increase" }}
          icon={Key}
          variant="default"
        />
        <MetricCard
          title="MFA Coverage"
          value="60%"
          change={{ value: "+20% this month", type: "increase" }}
          icon={Settings}
          variant="warning"
        />
      </div>

      <Tabs defaultValue="users" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="permissions">Permissions</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>User Directory</CardTitle>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input 
                    placeholder="Search users..." 
                    className="pl-8 w-64"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <Select value={roleFilter} onValueChange={setRoleFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Filter by role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Roles</SelectItem>
                    <SelectItem value="Admin">Admin</SelectItem>
                    <SelectItem value="SecurityAnalyst">Security Analyst</SelectItem>
                    <SelectItem value="User">User</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                    <SelectItem value="suspended">Suspended</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Department</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead>MFA</TableHead>
                    <TableHead>API Keys</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Avatar className="h-8 w-8">
                            <AvatarImage src={user.avatar} />
                            <AvatarFallback>{user.name.split(' ').map(n => n[0]).join('')}</AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium">{user.name}</p>
                            <p className="text-sm text-muted-foreground">{user.email}</p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getRoleBadgeVariant(user.role)} className={getRoleColor(user.role)}>
                          {user.role}
                        </Badge>
                      </TableCell>
                      <TableCell>{user.department}</TableCell>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(user.status)} className={getStatusColor(user.status)}>
                          {user.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{user.lastLogin}</TableCell>
                      <TableCell>
                        {user.mfaEnabled ? (
                          <Badge variant="default">Enabled</Badge>
                        ) : (
                          <Badge variant="secondary">Disabled</Badge>
                        )}
                      </TableCell>
                      <TableCell>{user.apiKeyCount}</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Edit className="h-4 w-4 mr-2" />
                              Edit User
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <UserX className="h-4 w-4 mr-2" />
                              Suspend User
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-critical">
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete User
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api-keys" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                API Key Management
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Key</TableHead>
                    <TableHead>Owner</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead>Usage</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockApiKeys.map((apiKey) => (
                    <TableRow key={apiKey.id}>
                      <TableCell className="font-medium">{apiKey.name}</TableCell>
                      <TableCell className="font-mono text-sm">{apiKey.key.substring(0, 20)}...</TableCell>
                      <TableCell>{apiKey.userName}</TableCell>
                      <TableCell>{apiKey.created}</TableCell>
                      <TableCell className="font-mono text-sm">{apiKey.lastUsed}</TableCell>
                      <TableCell>{apiKey.usage}</TableCell>
                      <TableCell>
                        <Badge variant="default">Active</Badge>
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem>
                              <Edit className="h-4 w-4 mr-2" />
                              Edit Key
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <UserX className="h-4 w-4 mr-2" />
                              Revoke Key
                            </DropdownMenuItem>
                            <DropdownMenuItem className="text-critical">
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete Key
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="permissions" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Role-Based Access Control</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Admin</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Full System Access</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">User Management</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">API Key Management</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Model Retraining</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Settings Management</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Security Analyst</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Dashboard Access</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Incident Management</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Model Monitoring</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Alert Configuration</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">User Management</span>
                        <Badge variant="secondary">✗</Badge>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">User</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Dashboard View</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Alert View</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Report Generation</span>
                        <Badge variant="default">✓</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Incident Management</span>
                        <Badge variant="secondary">✗</Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">System Configuration</span>
                        <Badge variant="secondary">✗</Badge>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}