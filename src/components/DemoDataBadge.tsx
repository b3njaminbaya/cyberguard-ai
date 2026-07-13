import { FlaskConical } from "lucide-react"

export function DemoDataBadge() {
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground border border-border/60 rounded-full px-2.5 py-1 w-fit">
      <FlaskConical className="h-3 w-3" />
      Demo data — backend for this page isn't built yet
    </div>
  )
}
