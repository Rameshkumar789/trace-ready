import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { mapWorkbookToOntology } from "@/lib/mapping/workbook-to-ontology";
import { evaluateEntityScope, evaluateProductScope } from "./scope-evaluators";

describe("scope evaluators", () => {
  it("links not-determined entity and product scope to source-backed findings", () => {
    const { ruleCards } = loadRegulatoryBundle();
    const dataset = mapWorkbookToOntology({
      "00_Business_Profile": [{ business_id: "biz", company_name: "Co", handles_ftl_foods: "yes", covered_entity_status: "not_determined" }],
      "01_Product_Master": [{ product_id: "p1", product_name: "Unknown Item", ftl_food_category: "", is_ftl_maybe: "unknown" }]
    });
    expect(evaluateEntityScope(dataset, ruleCards)[0]?.status).toBe("not_determined");
    expect(evaluateProductScope(dataset, ruleCards)[0]?.status).toBe("not_determined");
  });
});
