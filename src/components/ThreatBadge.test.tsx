import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { ThreatBadge } from "./ThreatBadge"

describe("ThreatBadge", () => {
  it.each(["critical", "high", "medium", "low"] as const)("renders the %s level as visible text", (level) => {
    render(<ThreatBadge level={level} />)
    expect(screen.getByText(level)).toBeInTheDocument()
  })

  it("applies severity-specific styling so critical and low are visually distinct", () => {
    const { container: criticalContainer } = render(<ThreatBadge level="critical" />)
    const { container: lowContainer } = render(<ThreatBadge level="low" />)
    expect(criticalContainer.firstChild?.textContent).not.toBe(lowContainer.firstChild?.textContent)
    expect(criticalContainer.querySelector(".bg-critical")).not.toBeNull()
    expect(lowContainer.querySelector(".bg-low")).not.toBeNull()
  })
})
