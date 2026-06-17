import { describe, expect, it } from "vitest";
import { normalizeDate } from "./date-normalizer";
import { normalizeQuantity } from "./quantity-normalizer";
import { normalizeUnit } from "./unit-normalizer";
import { normalizeTlc } from "./tlc-normalizer";

describe("normalization", () => {
  it("normalizes dates, quantities, units, and TLCs without silently inventing values", () => {
    expect(normalizeDate("2026-06-14")).toBe("2026-06-14");
    expect(normalizeDate("not a date")).toBeUndefined();
    expect(normalizeQuantity("1,250")).toBe(1250);
    expect(normalizeUnit(" Cases ")).toBe("cases");
    expect(normalizeTlc(" tlc-1 ")).toBe("TLC-1");
    expect(normalizeTlc(" ")).toBeUndefined();
  });
});
