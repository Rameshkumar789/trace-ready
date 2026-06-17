import { describe, expect, it } from "vitest";
import { mapFindingRow } from "./operator-audit-db";

describe("operator audit DB mapping", () => {
  it("maps persisted audit findings into the UI finding shape", () => {
    const finding = mapFindingRow({
      id: "finding_1",
      title: "Missing shipping KDE",
      status: "gap",
      severity: "high",
      finding_type: "kde_completeness",
      event_id: "event_1",
      event_line_id: null,
      field_or_kde: "ship_to_location",
      observed_value: null,
      expected_or_required: "Ship-to location must be retained.",
      recommendation: "Capture the missing ship-to location.",
      rule_card_id: null,
      rule_card_version: null,
      approved_record_id: "approved_record_1",
      approved_obligation_id: "obligation_1",
      source_chunk_id: null,
      kde_requirement_id: "kde_req_1",
      rule_package_id: "approved-rule-package-v1",
      rule_package_version: 1,
      check_code: "shipping_kde",
      evidence_refs_json: ["evidence_1"],
      metadata_json: {
        sourceCitation: {
          section: "21 CFR 1.1340"
        }
      },
      review_state: "needs_more_evidence",
      created_at: "2026-06-16T00:00:00.000Z"
    });

    expect(finding).toMatchObject({
      findingId: "finding_1",
      status: "gap",
      severity: "high",
      findingType: "kde_completeness",
      ruleCardId: "approved_record_1",
      ruleCardVersion: 1,
      sourceChunkId: "21 CFR 1.1340",
      kdeRequirementId: "kde_req_1",
      reviewState: "needs_more_evidence",
      evidenceRefs: [{ evidenceId: "evidence_1" }]
    });
  });
});
