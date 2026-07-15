import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { AuthProvider, useAuth } from "@/lib/AuthContext";
import { OrgProvider } from "@/lib/OrgContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { RequireOrganization } from "@/components/RequireOrganization";
import { OrgSwitcher } from "@/components/OrgSwitcher";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import Threats from "./pages/Threats";
import Incidents from "./pages/Incidents";
import Models from "./pages/Models";
import Network from "./pages/Network";
import Logs from "./pages/Logs";
import Users from "./pages/Users";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function UserMenu() {
  const { user, signOut } = useAuth();
  return (
    <div className="ml-auto flex items-center gap-3">
      <span className="text-sm text-muted-foreground">{user?.email}</span>
      <Button variant="ghost" size="sm" onClick={signOut}>
        <LogOut className="h-4 w-4 mr-1" />
        Sign Out
      </Button>
    </div>
  );
}

function Dashboard() {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full bg-gradient-matrix">
        <AppSidebar />
        <div className="flex-1 flex flex-col">
          <header className="h-14 border-b border-border/50 backdrop-blur-sm bg-background/50 flex items-center px-4 gap-4">
            <SidebarTrigger />
            <OrgSwitcher />
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-success animate-pulse"></div>
              <span className="text-sm text-muted-foreground">All systems operational</span>
            </div>
            <UserMenu />
          </header>
          <main className="flex-1 overflow-auto">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/threats" element={<Threats />} />
              <Route path="/incidents" element={<Incidents />} />
              <Route path="/models" element={<Models />} />
              <Route path="/network" element={<Network />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/users" element={<Users />} />
              <Route path="/settings" element={<Settings />} />
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <OrgProvider>
                    <RequireOrganization>
                      <Dashboard />
                    </RequireOrganization>
                  </OrgProvider>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
