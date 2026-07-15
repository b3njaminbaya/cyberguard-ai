import { createAuthClient } from "@neondatabase/auth"
import { BetterAuthVanillaAdapter, SupabaseAuthAdapter } from "@neondatabase/auth/vanilla/adapters"

const AUTH_URL = import.meta.env.VITE_NEON_AUTH_URL as string

export const authClient = createAuthClient(AUTH_URL, {
  adapter: SupabaseAuthAdapter(),
})

// SupabaseAuthAdapter's public surface only implements Supabase-shaped
// methods (signInWithPassword, getSession, etc.) — at runtime it does NOT
// proxy the `organization` plugin, even though its TypeScript types imply
// it does (verified by reading the adapter's actual .mjs, not just the
// .d.ts — the .d.ts overstates what SupabaseAuthAdapterImpl implements).
// BetterAuthVanillaAdapter returns the raw Better Auth client instead,
// which has every registered client plugin (organization included) at the
// top level. Both clients hit the same AUTH_URL and share the same
// browser session cookie, so signing in via `authClient` is enough — no
// separate sign-in needed for orgClient.
export const orgClient = createAuthClient(AUTH_URL, {
  adapter: BetterAuthVanillaAdapter(),
})

export async function getAccessToken(): Promise<string | null> {
  const { data } = await authClient.getSession()
  return data?.session?.access_token ?? null
}
