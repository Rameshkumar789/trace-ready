import { describe, expect, it } from "vitest";
import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import { runTracebackFireDrill } from "./fire-drill";

function dataset(): NormalizedAuditDataset {
  return {
    businessProfiles: [],
    exemptionClaims: [],
    products: [],
    productScopeDecisions: [],
    traceabilityPlans: [],
    events: [
      { eventId: "R", eventType: "receiving" },
      { eventId: "S", eventType: "shipping" }
    ],
    lineItems: [
      { eventLineId: "l1", eventId: "R", productId: "P", productName: "X", lotOrTlc: "LOT-1" },
      { eventLineId: "l2", eventId: "S", productId: "P", productName: "X", lotOrTlc: "LOT-1" }
    ],
    kdeValues: [],
    lineage: [],
    sourceDocuments: []
  } as unknown as NormalizedAuditDataset;
}

describe("traceback fire-drill", () => {
  it("passes with a full one-up/one-down chain", () => {
    const r = runTracebackFireDrill(dataset(), "LOT-1");
    expect(r.passed).toBe(true);
    expect(r.completenessScore).toBe(1);
    expect(r.oneUpLinked && r.oneDownLinked).toBe(true);
  });

  it("flags a missing one-down destination", () => {
    const d = dataset();
    d.events = [{ eventId: "R", eventType: "receiving" }] as NormalizedAuditDataset["events"];
    d.lineItems = [{ eventLineId: "l1", eventId: "R", productId: "P", productName: "X", lotOrTlc: "LOT-1" }] as NormalizedAuditDataset["lineItems"];
    const r = runTracebackFireDrill(d, "LOT-1");
    expect(r.passed).toBe(false);
    expect(r.oneDownLinked).toBe(false);
    expect(r.missingLinks.some((m) => m.includes("one-down"))).toBe(true);
  });

  it("handles an unknown lot", () => {
    expect(runTracebackFireDrill(dataset(), "NOPE").completenessScore).toBe(0);
  });
});
