import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "./data-loader";
import { mapWorkbookToOntology } from "@/lib/mapping/workbook-to-ontology";
import { evaluateExemptions } from "./exemption-evaluator";

describe("exemption evaluator", () => {
  it("marks missing exemption evidence as not determined", () => {
    const { ruleCards } = loadRegulatoryBundle();
    const dataset = mapWorkbookToOntology({
      "10_Exemptions_Claims": [
        { claim_id: "claim-1", claim_type: "small_producer", claimed_by: "Supplier A", evidence_provided: "no" }
      ]
    });
    const findings = evaluateExemptions(dataset, ruleCards);
    expect(findings[0]?.status).toBe("not_determined");
  });
});
