import { describe, expect, it } from "vitest";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import { buildAuditExportPackage } from "./export-package";
import type { StoredAudit } from "@/lib/audit/stored-audit";

describe("export package", () => {
  it("creates findings, summary, and sortable export check artifacts from one audit object", () => {
    const audit = runDemoAudit();
    const stored: StoredAudit = {
      auditId: "demo",
      createdAt: "2026-06-14T00:00:00.000Z",
      fileName: "demo.xlsx",
      parseErrors: [],
      dataset: {
        businessProfiles: [],
        exemptionClaims: [],
        products: [],
        productScopeDecisions: [],
        traceabilityPlans: [],
        events: [{ eventId: "rec-1", eventType: "receiving" }],
        lineItems: [],
        kdeValues: [],
        lineage: [],
        sourceDocuments: [{ evidenceId: "ev-1", eventId: "rec-1", evidenceType: "invoice", evidenceStatus: "available" }]
      },
      findings: audit.findings,
      readinessGate: audit.readinessGate,
      coverage: audit.coverage,
      mode: "draft"
    };
    const artifact = buildAuditExportPackage(stored);
    expect(artifact["11_Bellwether_Findings"].length).toBeGreaterThan(0);
    expect(artifact["12_Readiness_Summary"].some((row) => row.metric === "readiness_gate")).toBe(true);
    expect(artifact["13_FDA_Sortable_Export_Check"][0]?.has_source_document).toBe("yes");
  });
});
