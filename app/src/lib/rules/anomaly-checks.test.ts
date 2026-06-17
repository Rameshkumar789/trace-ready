import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { mapWorkbookToOntology } from "@/lib/mapping/workbook-to-ontology";
import { evaluateAnomalies } from "./anomaly-checks";

describe("anomaly checks", () => {
  it("reports duplicate reference records as operational anomalies", () => {
    const { ruleCards } = loadRegulatoryBundle();
    const dataset = mapWorkbookToOntology({
      "05_CTE_Events": [
        { event_id: "a", event_type: "shipping", event_datetime: "2026-06-14", actor_location_id: "loc", reference_record_no: "BOL-1" },
        { event_id: "b", event_type: "receiving", event_datetime: "2026-06-14", actor_location_id: "loc", reference_record_no: "BOL-1" }
      ]
    });
    expect(evaluateAnomalies(dataset, ruleCards)[0]?.status).toBe("operational_anomaly");
  });
});
