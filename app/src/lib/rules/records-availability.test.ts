import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { mapWorkbookToOntology } from "@/lib/mapping/workbook-to-ontology";
import { evaluateRecordsAvailability } from "./records-availability";

describe("records availability", () => {
  it("flags events without linked source documents", () => {
    const { ruleCards } = loadRegulatoryBundle();
    const dataset = mapWorkbookToOntology({
      "05_CTE_Events": [{ event_id: "ship-1", event_type: "shipping", event_datetime: "2026-06-14", actor_location_id: "loc-1" }],
      "09_Source_Documents": []
    });
    expect(evaluateRecordsAvailability(dataset, ruleCards)[0]?.findingType).toBe("sortable_export_gap");
  });
});
