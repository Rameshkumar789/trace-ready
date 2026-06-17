import { describe, expect, it } from "vitest";
import { runDemoAudit } from "./demo-audit";

describe("audit orchestrator", () => {
  it("produces deterministic source-backed findings for the demo audit", () => {
    const first = runDemoAudit();
    const second = runDemoAudit();
    expect(first.findings.map((finding) => finding.findingId)).toEqual(second.findings.map((finding) => finding.findingId));
    expect(first.findings.every((finding) => finding.ruleCardId && finding.sourceChunkId && finding.evidenceRefs.length)).toBe(true);
  });

  it("keeps customer-facing output behind the readiness gate while review is pending", () => {
    const audit = runDemoAudit();
    expect(audit.readinessGate.passed).toBe(false);
    expect(audit.readinessGate.blockers.some((blocker) => blocker.includes("approved human review"))).toBe(true);
  });
});
