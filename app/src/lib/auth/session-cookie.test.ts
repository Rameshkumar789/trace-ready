import { describe, expect, it } from "vitest";
import {
  canAccessPath,
  createSupabaseSession,
  defaultRedirectForRole,
  parseSessionCookie,
  serializeSession
} from "./session-cookie";

describe("TraceReady role sessions", () => {
  process.env.TRACEREADY_AUTH_SECRET = "test-secret-with-enough-entropy-for-hmac";

  it("serializes and parses signed Supabase-backed sessions", async () => {
    const session = createSupabaseSession({
      userId: "supabase-user-1",
      email: "Ops@Example.com",
      fullName: "Operations Lead",
      companyName: "Example Produce",
      role: "operator",
      expiresAt: Date.now() + 60_000
    });
    const parsed = await parseSessionCookie(await serializeSession(session));
    expect(parsed?.email).toBe("ops@example.com");
    expect(parsed?.fullName).toBe("Operations Lead");
    expect(parsed?.companyName).toBe("Example Produce");
    expect(parsed?.role).toBe("operator");
    expect(parsed?.authProvider).toBe("supabase");
  });

  it("rejects tampered sessions", async () => {
    const session = createSupabaseSession({
      userId: "supabase-user-1",
      email: "ops@example.com",
      role: "operator",
      expiresAt: Date.now() + 60_000
    });
    const cookie = await serializeSession(session);
    expect(await parseSessionCookie(`${cookie}tampered`)).toBeUndefined();
  });

  it("separates operator and regulatory access", () => {
    const operator = createSupabaseSession({
      userId: "operator-user",
      email: "operator@example.com",
      role: "operator",
      expiresAt: Date.now() + 60_000
    });
    const reviewer = createSupabaseSession({
      userId: "reviewer-user",
      email: "reviewer@example.com",
      role: "fsma_reviewer",
      expiresAt: Date.now() + 60_000
    });
    expect(canAccessPath(operator, "/operator")).toBe(true);
    expect(canAccessPath(operator, "/upload")).toBe(true);
    expect(canAccessPath(operator, "/admin/regulatory/review")).toBe(false);
    expect(canAccessPath(reviewer, "/reviewer")).toBe(true);
    expect(canAccessPath(reviewer, "/admin/regulatory/review")).toBe(true);
    expect(canAccessPath(reviewer, "/upload")).toBe(false);
  });

  it("routes roles to the right first workspace", () => {
    expect(defaultRedirectForRole("operator")).toBe("/operator");
    expect(defaultRedirectForRole("fsma_reviewer")).toBe("/reviewer");
  });
});
