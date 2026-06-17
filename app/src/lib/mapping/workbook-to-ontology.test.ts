import { describe, expect, it } from "vitest";
import { mapWorkbookToOntology } from "./workbook-to-ontology";

describe("workbook to ontology mapper", () => {
  it("maps required workbook sheets into ontology objects without dropping ambiguous rows", () => {
    const dataset = mapWorkbookToOntology({
      "00_Business_Profile": [
        {
          business_id: "biz-1",
          company_name: "Pilot Foods",
          business_type: "processor",
          handles_ftl_foods: "yes",
          covered_entity_status: ""
        }
      ],
      "01_Product_Master": [
        {
          product_id: "prod-1",
          product_name: "Fresh salsa",
          ftl_food_category: "Fresh-cut vegetables",
          is_ftl_maybe: ""
        }
      ],
      "05_CTE_Events": [
        {
          event_id: "transform-1",
          event_type: "transformation",
          event_datetime: "2026-06-14T08:00:00Z",
          actor_location_id: "loc-1"
        }
      ],
      "07_KDE_Values": [
        {
          kde_id: "kde-1",
          event_id: "transform-1",
          cte_type: "transformation",
          kde_name: "Transformation reference record",
          field_key: "transformation_reference_record",
          kde_value: ""
        }
      ],
      "08_TLC_Lineage": [
        {
          lineage_id: "lin-1",
          relationship_type: "transformed_into",
          source_event_id: "receive-1",
          source_lot_or_tlc: "TLC-IN",
          target_event_id: "transform-1",
          target_lot_or_tlc: "TLC-OUT",
          lineage_status: "unverified"
        }
      ],
      "10_Exemptions_Claims": [
        {
          claim_id: "claim-1",
          claim_type: "kill_step",
          claimed_by: "biz-1",
          evidence_provided: "no"
        }
      ]
    });

    expect(dataset.businessProfiles[0]?.coveredEntityStatus).toBe("not_determined");
    expect(dataset.productScopeDecisions[0]?.status).toBe("not_determined");
    expect(dataset.events[0]?.eventType).toBe("transformation");
    expect(dataset.kdeValues[0]?.status).toBe("missing");
    expect(dataset.lineage[0]?.lineageStatus).toBe("unverified");
    expect(dataset.exemptionClaims[0]?.decision).toBe("not_determined");
  });
});
