import { describe, expect, it } from "vitest"
import { computeProtocolCounts, computeTopTalkers } from "./Network"

describe("computeProtocolCounts", () => {
  it("groups events by protocol and sums bytes", () => {
    const result = computeProtocolCounts([
      { protocol: "tcp", bytes: 100 },
      { protocol: "tcp", bytes: 50 },
      { protocol: "udp", bytes: 10 },
    ])
    expect(result).toEqual([
      { protocol: "tcp", count: 2, bytes: 150 },
      { protocol: "udp", count: 1, bytes: 10 },
    ])
  })

  it("sorts by descending count", () => {
    const result = computeProtocolCounts([
      { protocol: "udp", bytes: 1 },
      { protocol: "tcp", bytes: 1 },
      { protocol: "tcp", bytes: 1 },
      { protocol: "tcp", bytes: 1 },
    ])
    expect(result.map((r) => r.protocol)).toEqual(["tcp", "udp"])
  })

  it("returns an empty array for no events", () => {
    expect(computeProtocolCounts([])).toEqual([])
  })
})

describe("computeTopTalkers", () => {
  it("aggregates flows and bytes per source IP", () => {
    const result = computeTopTalkers(
      [
        { source_ip: "10.0.0.1", bytes: 100 },
        { source_ip: "10.0.0.1", bytes: 200 },
        { source_ip: "10.0.0.2", bytes: 50 },
      ],
      new Set()
    )
    expect(result).toEqual([
      { ip: "10.0.0.1", flows: 2, bytes: 300, flagged: false },
      { ip: "10.0.0.2", flows: 1, bytes: 50, flagged: false },
    ])
  })

  it("sorts by descending bytes, not flow count", () => {
    const result = computeTopTalkers(
      [
        { source_ip: "low-bytes-many-flows", bytes: 1 },
        { source_ip: "low-bytes-many-flows", bytes: 1 },
        { source_ip: "low-bytes-many-flows", bytes: 1 },
        { source_ip: "high-bytes-one-flow", bytes: 1000 },
      ],
      new Set()
    )
    expect(result[0].ip).toBe("high-bytes-one-flow")
  })

  it("marks a host as flagged when its IP appears in the flagged set", () => {
    const result = computeTopTalkers(
      [{ source_ip: "10.0.0.9", bytes: 1 }],
      new Set(["10.0.0.9"])
    )
    expect(result[0].flagged).toBe(true)
  })
})
