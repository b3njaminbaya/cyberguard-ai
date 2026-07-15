import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Shield, AlertTriangle } from "lucide-react"
import { useAuth } from "@/lib/AuthContext"

export default function Login() {
  const { signIn, signUp, signInWithGoogle } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [googleSubmitting, setGoogleSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    const { error } = mode === "sign-in" ? await signIn(email, password) : await signUp(email, password)
    setSubmitting(false)
    if (error) {
      setError(error)
      return
    }
    navigate("/")
  }

  const handleGoogle = async () => {
    setGoogleSubmitting(true)
    setError(null)
    const { error } = await signInWithGoogle()
    // On success this redirects the whole page to Google — there's no
    // "then" to navigate() from. Only reachable on failure.
    setGoogleSubmitting(false)
    if (error) setError(error)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-matrix p-6">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            <CardTitle>CyberGuard AI</CardTitle>
          </div>
          <CardDescription>
            {mode === "sign-in" ? "Sign in to view the threat dashboard" : "Create an account"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            {error && (
              <div className="flex items-start gap-2 text-sm text-critical">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Please wait…" : mode === "sign-in" ? "Sign In" : "Create Account"}
            </Button>
          </form>

          <div className="flex items-center gap-2 my-4">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <Button type="button" variant="outline" className="w-full" disabled={googleSubmitting} onClick={handleGoogle}>
            {googleSubmitting ? "Redirecting…" : "Continue with Google"}
          </Button>

          <button
            type="button"
            className="mt-4 text-sm text-muted-foreground hover:text-foreground w-full text-center"
            onClick={() => { setMode(mode === "sign-in" ? "sign-up" : "sign-in"); setError(null) }}
          >
            {mode === "sign-in" ? "Need an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </CardContent>
      </Card>
    </div>
  )
}
