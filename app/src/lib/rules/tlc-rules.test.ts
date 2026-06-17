import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { mapWorkbookToOntology } from "@/lib/mapping/workbook-to-ontology";
import { evaluateTlcAssignment } from "./tlc-assignment";
import { evaluateTlcLineage } from "./tlc-lineage";

describe("TLC rules", () => {
  it("creates distinct missing TLC and lineage gap findings", () => {
    const { ruleCards } = loadRegulatoryBundle();
    const dataset = mapWorkbookToOntology({
      "06_Event_Line_Items": [
        { event_line_id: "line-1", event_id: "rec-1", product_id: "p1", product_name: "Fresh Basil", lot_or_tlc: "" }
      ],
      "08_TLC_Lineage": [
        { lineage_id: "lin-1", relationship_type: "received_to_transformed", source_lot_or_tlc: "", target_lot_or_tlc: "TLC-2", lineage_status: "gap" }
      ]
    });
    expect(evaluateTlcAssignment(dataset, ruleCards)[0]?.findingType).toBe("tlc_assignment_gap");
    expect(evaluateTlcLineage(dataset, ruleCards)[0]?.findingType).toBe("lineage_gap");
  });
});
