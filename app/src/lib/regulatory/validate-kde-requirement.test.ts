import { describe, expect, it } from "vitest";
import { loadRegulatoryBundle } from "./data-loader";
import { validateKdeRequirement } from "./validate-kde-requirement";

describe("KDE requirement validation", () => {
  it("requires approved KDEs to link to source chunks and rule cards", () => {
    const { kdeRequirements, chunks, ruleCards } = loadRegulatoryBundle();
    for (const requirement of kdeRequirements) {
      expect(validateKdeRequirement(requirement, chunks, ruleCards).valid).toBe(true);
    }
  });
});
