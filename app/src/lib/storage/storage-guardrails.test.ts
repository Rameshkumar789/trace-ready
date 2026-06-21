import { afterEach, describe, expect, it, vi } from "vitest";
import { getStorageProvider } from "./supabase-storage";

describe("production storage guardrails", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("fails loudly when production object storage env is missing", () => {
    vi.stubEnv("BELLWETHER_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "");

    expect(() => getStorageProvider()).toThrow("Non-durable memory storage is disabled in production");
  });

  it("allows memory storage only through an explicit production override", () => {
    vi.stubEnv("BELLWETHER_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "");
    vi.stubEnv("BELLWETHER_ALLOW_MEMORY_STORAGE", "true");

    expect(getStorageProvider().constructor.name).toBe("LocalMemoryStorageProvider");
  });
});
