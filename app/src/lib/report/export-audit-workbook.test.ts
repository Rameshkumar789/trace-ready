import { describe, expect, it } from "vitest";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import { exportAuditWorkbookBuffer } from "./export-audit-workbook";

describe("audit workbook export", () => {
  it("generates a non-empty XLSX buffer", async () => {
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
        events: [],
        lineItems: [],
        kdeValues: [],
        lineage: [],
        sourceDocuments: []
      },
      findings: audit.findings,
      readinessGate: audit.readinessGate,
      coverage: audit.coverage,
      mode: "draft"
    };
    const buffer = await exportAuditWorkbookBuffer(stored);
    expect(buffer.byteLength).toBeGreaterThan(1000);
  });
});
