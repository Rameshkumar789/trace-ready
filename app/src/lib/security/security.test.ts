import { describe, expect, it } from "vitest";
import { validateUploadMetadata } from "./upload-security";

describe("pilot security checks", () => {
  it("allows only Excel uploads under the pilot size limit", () => {
    expect(validateUploadMetadata("pilot.xlsx", 1000).valid).toBe(true);
    expect(validateUploadMetadata("pilot.xlsm", 1000).valid).toBe(true);
    expect(validateUploadMetadata("pilot.xls", 1000).valid).toBe(false);
    expect(validateUploadMetadata("pilot.pdf", 1000).valid).toBe(false);
    expect(validateUploadMetadata("pilot.xlsx", 20 * 1024 * 1024).valid).toBe(false);
  });
});
