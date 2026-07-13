import { createAuthClient } from "@neondatabase/auth"
import { SupabaseAuthAdapter } from "@neondatabase/auth/vanilla/adapters"

const AUTH_URL = import.meta.env.VITE_NEON_AUTH_URL as string

export const authClient = createAuthClient(AUTH_URL, {
  adapter: SupabaseAuthAdapter(),
})

export async function getAccessToken(): Promise<string | null> {
  const { data } = await authClient.getSession()
  return data?.session?.access_token ?? null
}
