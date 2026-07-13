import { AlertTriangle, Loader2 } from "lucide-react"

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <AlertTriangle className="h-8 w-8 text-critical" />
      <p className="text-sm font-medium">Couldn't reach the backend</p>
      <p className="text-xs text-muted-foreground max-w-sm">{message}</p>
      <p className="text-xs text-muted-foreground">
        Is the API running? <code className="font-mono">cd backend && uvicorn main:app --reload</code>
      </p>
    </div>
  )
}
