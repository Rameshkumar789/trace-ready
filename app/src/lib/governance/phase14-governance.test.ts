import { describe, expect, it } from "vitest";
import { createFinding } from "@/lib/findings/finding";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import {
  applyFindingReviewAction,
  applyReviewerOverride,
  buildAuditPackagePin,
  buildExplainabilityTraces,
  initializePhase14Governance,
  promoteReviewerOverride
} from "./phase14-governance";

function auditFixture(): StoredAudit {
  return {
    auditId: "audit-1",
    createdAt: "2026-06-16T00:00:00Z",
    fileName: "customer.xlsx",
    parseErrors: [],
    dataset: {
      businessProfiles: [],
      exemptionClaims: [],
      products: [],
      productScopeDecisions: [],
      traceabilityPlans: [],
      events: [{ eventId: "ship-1", eventType: "shipping", eventDatetime: "2026-06-12" }],
      lineItems: [{ eventLineId: "line-1", eventId: "ship-1", productId: "prod-1", productName: "Fresh Basil" }],
      kdeValues: [],
      lineage: [],
      sourceDocuments: []
    },
    findings: [
      createFinding({
        title: "Missing TLC",
        status: "gap",
        severity: "high",
        findingType: "kde_completeness",
        eventId: "ship-1",
        eventLineId: "line-1",
        fieldOrKde: "traceability_lot_code",
        expectedOrRequired: "TLC is required",
        recommendation: "Add the traceability lot code.",
        ruleCardId: "FSMA204-OBL-DET-1340-SHIPPING-KDES",
        ruleCardVersion: 1,
        sourceChunkId: "ecfr-21-cfr-1-subpart-s-21-cfr-1-1340-9",
        regulatorySourceId: "ecfr-21-cfr-1-subpart-s",
        evidenceRefs: [{ sheet: "05_CTE_Events", row: 4, field: "lot_or_tlc" }]
      })
    ],
    readinessGate: { passed: false, blockers: ["Findings require approved human review."] },
    coverage: [],
    mode: "draft",
    governance: initializePhase14Governance("audit-1")
  };
}

describe("phase14 governance", () => {
  it("pins package and parser versions for an audit", () => {
    const pin = buildAuditPackagePin({
      rulePackage: { package_id: "approved-rule-package-v1", version: 1, scenario_regression_gate: { status: "pass" } },
      phase10Summary: { generatedAt: "2026-06-16T00:00:00Z", evidenceRecords: 80, eventNodes: 3 },
      phase13Summary: { twoStageStatus: "pass", subparagraphResolutionStatus: "pass" }
    });

    expect(pin.rulePackageId).toBe("approved-rule-package-v1");
    expect(pin.customerEvidenceVersion).toContain("80:3");
    expect(pin.parserVersions).toContain("phase13-two-stage:pass");
  });

  it("appends immutable review actions and updates finding state", () => {
    const updated = applyFindingReviewAction(auditFixture(), {
      findingId: "finding-fsma204-obl-det-1340-shipping-kdes-ship-1-line-1-traceability-lot-code",
      reviewer: "reviewer@example.com",
      action: "approve",
      reason: "Source evidence reviewed."
    });

    expect(updated.findings[0]?.reviewState).toBe("approved");
    expect(updated.governance?.reviewActionLog.at(-1)?.immutable).toBe(true);
    expect(updated.governance?.reviewActionLog.at(-1)?.reason).toBe("Source evidence reviewed.");
  });

  it("keeps reviewer overrides excluded until promoted by approval", () => {
    const overridden = applyReviewerOverride(auditFixture(), {
      findingId: "finding-fsma204-obl-det-1340-shipping-kdes-ship-1-line-1-traceability-lot-code",
      reviewer: "reviewer@example.com",
      reason: "Customer supplied alternate proof outside the workbook."
    });
    const override = overridden.governance?.reviewerOverrides[0];
    expect(override?.status).toBe("excluded_from_automation");

    const promoted = promoteReviewerOverride(overridden, {
      overrideId: override?.overrideId ?? "",
      reviewer: "lead@example.com",
      reason: "Approved for this audit only."
    });
    expect(promoted.governance?.reviewerOverrides[0]?.status).toBe("promoted_by_approval");
  });

  it("builds explainability traces from evidence to source citation", () => {
    const trace = buildExplainabilityTraces(auditFixture())[0];

    expect(trace?.steps.map((step) => step.step)).toEqual([
      "customer_evidence",
      "normalized_event",
      "deterministic_check",
      "approved_rule",
      "source_citation"
    ]);
    expect(trace?.steps[0]?.detail).toContain("05_CTE_Events row 4");
    expect(trace?.steps[4]?.detail).toContain("ecfr-21-cfr-1-subpart-s");
  });
});
