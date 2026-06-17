import { describe, expect, it } from "vitest";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import { evaluateReadinessGate } from "./readiness-gate";
import { loadRegulatoryBundle } from "./data-loader";

describe("readiness gate", () => {
  it("requires source/rule/KDE/evidence/review references on findings", () => {
    const audit = runDemoAudit();
    expect(audit.findings.length).toBeGreaterThan(0);
    expect(audit.readinessGate.blockers.every((blocker) => blocker.length > 0)).toBe(true);
  });

  it("blocks a finding without an approved rule card", () => {
    const bundle = loadRegulatoryBundle();
    const audit = runDemoAudit();
    const finding = { ...audit.findings[0], ruleCardId: "missing-rule" };
    const gate = evaluateReadinessGate({ ...bundle, findings: [finding] });
    expect(gate.passed).toBe(false);
    expect(gate.blockers.join(" ")).toContain("missing approved rule card");
  });

  it("requires an approved obligation inventory for the source and rule gate", () => {
    const bundle = loadRegulatoryBundle();
    const gate = evaluateReadinessGate({ ...bundle, obligations: [], findings: [] });
    expect(gate.passed).toBe(false);
    expect(gate.blockers.join(" ")).toContain("obligation inventory");
  });
});
