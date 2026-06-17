import { afterEach, describe, expect, it, vi } from "vitest";
import { LocalAuditRepository, getAuditRepository } from "./audit-repository";
import { PrismaStoredAuditRepository } from "./prisma-audit-repository";
import { listAudits } from "./local-audit-store";
import { getStorageProvider } from "./supabase-storage";

describe("production storage guardrails", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("fails loudly when production object storage env is missing", () => {
    vi.stubEnv("TRACEREADY_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "");

    expect(() => getStorageProvider()).toThrow("Non-durable memory storage is disabled in production");
  });

  it("allows memory storage only through an explicit production override", () => {
    vi.stubEnv("TRACEREADY_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "");
    vi.stubEnv("TRACEREADY_ALLOW_MEMORY_STORAGE", "true");

    expect(getStorageProvider().constructor.name).toBe("LocalMemoryStorageProvider");
  });

  it("returns the DB-backed audit repository in production", () => {
    vi.stubEnv("TRACEREADY_ENV", "production");
    vi.stubEnv("TRACEREADY_ALLOW_LOCAL_AUDIT_STORE", "");

    expect(getAuditRepository()).toBeInstanceOf(PrismaStoredAuditRepository);
  });

  it("uses the local audit repository outside production", () => {
    vi.stubEnv("TRACEREADY_ENV", "test");

    expect(getAuditRepository()).toBeInstanceOf(LocalAuditRepository);
  });

  it("blocks direct local audit JSON access in production", async () => {
    vi.stubEnv("TRACEREADY_ENV", "production");
    vi.stubEnv("TRACEREADY_ALLOW_LOCAL_AUDIT_STORE", "");

    await expect(listAudits()).rejects.toThrow("Local audit JSON storage is disabled in production");
  });
});
