import { describe, expect, it } from "vitest";
import { mapWorkbookToOntology } from "@/lib/mapping/workbook-to-ontology";
import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { evaluateSortableExportReadiness } from "./sortable-export-readiness";

describe("sortable export readiness", () => {
  it("reports rows that block a source-backed sortable response package", () => {
    const { ruleCards } = loadRegulatoryBundle();
    const dataset = mapWorkbookToOntology({
      "05_CTE_Events": [
        {
          event_id: "receive-1",
          event_type: "receiving",
          event_datetime: "2026-06-14T08:00:00Z",
          actor_location_id: "loc-1"
        }
      ],
      "09_Source_Documents": []
    });

    const findings = evaluateSortableExportReadiness(dataset, ruleCards);

    expect(findings).toHaveLength(1);
    expect(findings[0]).toMatchObject({
      findingType: "sortable_export_gap",
      status: "missing_evidence",
      eventId: "receive-1"
    });
  });
});
