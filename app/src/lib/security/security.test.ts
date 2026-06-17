import { describe, expect, it } from "vitest";
import { validateUploadMetadata } from "./upload-security";
import { canAccessAudit } from "./audit-access";

describe("pilot security checks", () => {
  it("allows only Excel uploads under the pilot size limit", () => {
    expect(validateUploadMetadata("pilot.xlsx", 1000).valid).toBe(true);
    expect(validateUploadMetadata("pilot.xlsm", 1000).valid).toBe(true);
    expect(validateUploadMetadata("pilot.xls", 1000).valid).toBe(false);
    expect(validateUploadMetadata("pilot.pdf", 1000).valid).toBe(false);
    expect(validateUploadMetadata("pilot.xlsx", 20 * 1024 * 1024).valid).toBe(false);
  });

  it("scopes audits to an authenticated owner", () => {
    expect(canAccessAudit("user-1", "user-1")).toBe(true);
    expect(canAccessAudit("user-2", "user-1")).toBe(false);
    expect(canAccessAudit(undefined, "user-1")).toBe(false);
  });

  it("scopes audits to org membership or founder admins", () => {
    expect(
      canAccessAudit(
        { userId: "user-1", role: "operator", customerIds: ["customer-1"] },
        { createdByUserId: "user-2", customerId: "customer-1" }
      )
    ).toBe(true);
    expect(
      canAccessAudit(
        { userId: "user-1", role: "operator", customerIds: ["customer-2"] },
        { createdByUserId: "user-2", customerId: "customer-1" }
      )
    ).toBe(false);
    expect(
      canAccessAudit(
        { userId: "admin-1", role: "founder_admin", customerIds: [] },
        { createdByUserId: "user-2", customerId: "customer-1" }
      )
    ).toBe(true);
  });
});
