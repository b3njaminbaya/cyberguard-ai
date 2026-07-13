import { Navigate } from "react-router-dom"
import { useAuth } from "@/lib/AuthContext"
import { LoadingState } from "@/components/QueryState"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) return <LoadingState label="Checking session…" />
  if (!user) return <Navigate to="/login" replace />

  return <>{children}</>
}
