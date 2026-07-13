import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/auth-client", () => ({
  getAccessToken: vi.fn().mockResolvedValue("fake-token"),
}))

import { api, ApiError } from "./api"

describe("api client", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("attaches the bearer token to every request", async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 })
    )
    await api.threats()
    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(init.headers.Authorization).toBe("Bearer fake-token")
  })

  it("surfaces the backend's real error detail message, not a generic one", async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Insufficient permissions" }), { status: 403 })
    )
    await expect(api.testSlack()).rejects.toMatchObject(
      new ApiError(403, "Insufficient permissions")
    )
  })

  it("falls back to a generic message when the error body isn't JSON", async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response("not json", { status: 500, statusText: "Internal Server Error" })
    )
    await expect(api.summary()).rejects.toThrow(/500/)
  })

  it("sends a JSON content-type header only when there's a body", async () => {
    ;(fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 })
    )
    await api.events()
    const [, getInit] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(getInit.headers["Content-Type"]).toBeUndefined()
  })
})
