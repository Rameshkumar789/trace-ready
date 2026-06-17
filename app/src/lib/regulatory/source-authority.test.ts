import { describe, expect, it } from "vitest";
import { loadRegulatorySources } from "./data-loader";
import { assertProposedRulesAreNotFinal, canOverride, sortByAuthority } from "./source-authority";

describe("source authority", () => {
  it("keeps proposed rules non-final", () => {
    const sources = loadRegulatorySources();
    expect(assertProposedRulesAreNotFinal(sources)).toEqual([]);
    expect(sources.find((source) => source.sourceId === "src-fr-2025-proposed-extension")?.isFinalized).toBe(false);
  });

  it("sorts higher authority sources before guidance and discussion material", () => {
    const sources = sortByAuthority(loadRegulatorySources());
    expect(sources[0]?.sourceStatus).toBe("codified_rule");
    expect(sources.at(-1)?.sourceStatus).toBe("discussion_paper");
  });

  it("does not let lower authority guidance override codified rule text", () => {
    const sources = loadRegulatorySources();
    const ecfr = sources.find((source) => source.sourceId === "src-ecfr-subpart-s-current")!;
    const faq = sources.find((source) => source.sourceId === "src-fda-faq")!;
    expect(canOverride(faq, ecfr)).toBe(false);
  });
});
