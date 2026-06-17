import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "./data-loader";
import { buildCitationAnchor } from "./citation-anchor";
import { chunkHasAuditCitation, findChunksByIds, getActiveChunks } from "./source-chunk";
import { chunkLegalMeaning } from "./source-chunker";

describe("source chunks", () => {
  it("chunks sources by legal meaning and preserves citations/hashes", () => {
    const { chunks } = loadRegulatoryBundle();
    expect(getActiveChunks(chunks).length).toBeGreaterThanOrEqual(14);
    expect(chunks.every(chunkHasAuditCitation)).toBe(true);
  });

  it("links every CTE chunk for rule-card generation", () => {
    const { chunks } = loadRegulatoryBundle();
    const cteChunkIds = [
      "chunk-harvest-cooling-1325",
      "chunk-initial-packing-1330",
      "chunk-first-land-based-receiving-1335",
      "chunk-shipping-1340",
      "chunk-receiving-1345",
      "chunk-transformation-1350"
    ];
    expect(findChunksByIds(chunks, cteChunkIds)).toHaveLength(cteChunkIds.length);
  });

  it("builds legal-meaning chunks with citation anchors and rejects split conditions", () => {
    const { sources } = loadRegulatoryBundle();
    const source = sources[0];
    const anchor = buildCitationAnchor({ source, section: "21 CFR 1.1340" });
    const chunks = chunkLegalMeaning(source, [
      {
        sectionLabel: "Shipping KDEs",
        section: "21 CFR 1.1340",
        text: "Shipping records must maintain TLC and immediate subsequent recipient KDEs."
      }
    ]);

    expect(anchor.citation).toContain("21 CFR 1.1340");
    expect(chunks[0]?.anchors?.[0]?.section).toBe("21 CFR 1.1340");
    expect(() =>
      chunkLegalMeaning(source, [{ sectionLabel: "Bad", section: "x", text: "When a covered food is shipped." }])
    ).toThrow("conditions");
  });
});
