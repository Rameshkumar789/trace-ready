import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "./data-loader";
import { chunkHasAuditCitation, findChunksByIds, getActiveChunks } from "./source-chunk";

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
});
