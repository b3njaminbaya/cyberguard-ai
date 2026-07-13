import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { authClient } from "@/lib/auth-client"
import { api } from "@/lib/api"

interface AuthUser {
  id: string
  email: string
  role: string | null
}

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<{ error: string | null }>
  signUp: (email: string, password: string) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function withRole(base: { id: string; email: string }): Promise<AuthUser> {
  try {
    const me = await api.me()
    return { ...base, role: me.role }
  } catch {
    // Role lookup is best-effort — a logged-in user without a resolvable
    // role just can't access Admin-gated actions, not a fatal error.
    return { ...base, role: null }
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    authClient.getSession().then(async ({ data }) => {
      if (data?.session?.user) {
        setUser(await withRole({ id: data.session.user.id, email: data.session.user.email }))
      }
      setIsLoading(false)
    })

    const { data: sub } = authClient.onAuthStateChange(async (_event, session) => {
      setUser(session?.user ? await withRole({ id: session.user.id, email: session.user.email }) : null)
    })

    return () => sub?.subscription?.unsubscribe?.()
  }, [])

  // Set user directly from the response rather than waiting on the
  // onAuthStateChange listener — navigating immediately after a successful
  // signIn/signUp can otherwise race ProtectedRoute's check against a user
  // state that hasn't been updated by the listener yet.
  const signIn = async (email: string, password: string) => {
    const { data, error } = await authClient.signInWithPassword({ email, password })
    if (data?.user) setUser(await withRole({ id: data.user.id, email: data.user.email }))
    return { error: error?.message ?? null }
  }

  const signUp = async (email: string, password: string) => {
    const { data, error } = await authClient.signUp({ email, password })
    if (data?.user) setUser(await withRole({ id: data.user.id, email: data.user.email }))
    return { error: error?.message ?? null }
  }

  const signOut = async () => {
    await authClient.signOut()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
