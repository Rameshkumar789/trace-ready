import { describe, expect, it } from "vitest";
import { canAccessPath, defaultRedirectForRole } from "./roles";

describe("operator access rules", () => {
  it("gates the operator workspace to operator-capable roles", () => {
    expect(canAccessPath({ role: "operator" }, "/operator")).toBe(true);
    expect(canAccessPath({ role: "operator" }, "/operator/upload")).toBe(true);
    expect(canAccessPath({ role: "operator" }, "/operator/audits")).toBe(true);
    expect(canAccessPath({ role: "founder_admin" }, "/operator")).toBe(true);
    // Bellwether is operator-only: reviewer-only roles no longer have a workspace.
    expect(canAccessPath({ role: "fsma_reviewer" }, "/operator")).toBe(false);
    expect(canAccessPath(undefined, "/operator")).toBe(false);
  });

  it("routes every role to the operator workspace", () => {
    expect(defaultRedirectForRole("operator")).toBe("/operator");
    expect(defaultRedirectForRole("fsma_reviewer")).toBe("/operator");
  });
});
