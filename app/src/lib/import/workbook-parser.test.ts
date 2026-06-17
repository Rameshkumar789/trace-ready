import { describe, expect, it } from "vitest";
import { validateParsedWorkbook } from "./workbook-parser";
import { parseWorkbook } from "./workbook-parser";
import fs from "node:fs";
import path from "node:path";

describe("workbook parser validation", () => {
  it("reports missing required sheets", () => {
    const errors = validateParsedWorkbook({});
    expect(errors.some((error) => error.sheet === "00_Business_Profile")).toBe(true);
  });

  it("reports missing required columns", () => {
    const errors = validateParsedWorkbook({
      "00_Business_Profile": [{ company_name: "Test Co" }]
    });
    expect(errors.some((error) => error.column === "business_id")).toBe(true);
  });

  it("parses the committed full audit sample workbook", async () => {
    const workbookPath = path.resolve(process.cwd(), "../data/samples/fsma204-full-audit-sample.xlsx");
    const buffer = fs.readFileSync(workbookPath);
    const parsed = await parseWorkbook(buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength));
    expect(parsed.errors).toEqual([]);
    expect(parsed.sheets["05_CTE_Events"]).toHaveLength(3);
  });
});
