import { describe, expect, it } from "vitest";
import { mapWorkbookToOntology } from "@/lib/mapping/workbook-to-ontology";
import { loadRegulatoryBundle } from "@/lib/regulatory/data-loader";
import { evaluateCteKdeCompleteness } from "./cte-kde-completeness";

describe("CTE/KDE completeness evaluator", () => {
  it("creates source-backed missing-KDE findings from approved CTE requirements", () => {
    const { kdeRequirements, ruleCards } = loadRegulatoryBundle();
    const dataset = mapWorkbookToOntology({
      "05_CTE_Events": [
        {
          event_id: "ship-1",
          event_type: "shipping",
          event_datetime: "2026-06-14T08:00:00Z",
          actor_location_id: "loc-1"
        }
      ],
      "07_KDE_Values": []
    });

    const findings = evaluateCteKdeCompleteness(dataset, kdeRequirements, ruleCards);

    expect(findings.length).toBeGreaterThan(0);
    expect(findings[0]).toMatchObject({
      status: "gap",
      findingType: "missing_kde",
      eventId: "ship-1"
    });
    expect(findings[0]?.ruleCardId).toBeTruthy();
    expect(findings[0]?.sourceChunkId).toBeTruthy();
    expect(findings[0]?.kdeRequirementId).toBeTruthy();
  });
});
