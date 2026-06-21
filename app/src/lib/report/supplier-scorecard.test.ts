import { describe, expect, it } from "vitest";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import { buildSupplierProductCoverage, buildSupplierScorecards } from "./supplier-scorecard";

function audit(): StoredAudit {
  return {
    dataset: {
      businessProfiles: [],
      exemptionClaims: [],
      products: [
        { productId: "P1", productName: "Romaine", isFtlMaybe: true },
        { productId: "P2", productName: "Crackers", isFtlMaybe: false }
      ],
      productScopeDecisions: [],
      traceabilityPlans: [],
      events: [
        { eventId: "E1", eventType: "shipping", fromPartnerId: "SUP-A" },
        { eventId: "E2", eventType: "shipping", fromPartnerId: "SUP-B" }
      ],
      lineItems: [
        { eventLineId: "L1", eventId: "E1", productId: "P1", productName: "Romaine" },
        { eventLineId: "L2", eventId: "E2", productId: "P2", productName: "Crackers" }
      ],
      kdeValues: [],
      lineage: [],
      sourceDocuments: []
    },
    findings: [
      {
        findingId: "f1", title: "Missing TLC", status: "gap", severity: "high",
        findingType: "tlc_lineage", eventId: "E1", fieldOrKde: "traceability_lot_code",
        recommendation: "add TLC", ruleCardId: "rc", ruleCardVersion: 1, sourceChunkId: "sc",
        evidenceRefs: [], reviewState: "pending"
      }
    ]
  } as unknown as StoredAudit;
}

describe("supplier scorecard derivation", () => {
  it("flags the in-scope supplier with a TLC gap and excludes off-list products", () => {
    const coverage = buildSupplierProductCoverage(audit());
    const byKey = Object.fromEntries(coverage.map((r) => [`${r.supplierId}/${r.product}`, r]));

    expect(byKey["SUP-A/Romaine"].status).toBe("gap");
    expect(byKey["SUP-A/Romaine"].tlcGap).toBe(true);
    expect(byKey["SUP-B/Crackers"].status).toBe("out_of_scope");
    expect(byKey["SUP-B/Crackers"].ftlStatus).toBe("off");
  });

  it("grades suppliers worst-first", () => {
    const cards = buildSupplierScorecards(audit());
    const a = cards.find((c) => c.supplierId === "SUP-A")!;
    expect(a.grade).toBe("F");
    expect(a.recommendedActions.some((x) => x.fieldOrIssue === "tlc_lineage")).toBe(true);
    expect(cards[0].supplierId).toBe("SUP-A"); // worst first
  });
});
