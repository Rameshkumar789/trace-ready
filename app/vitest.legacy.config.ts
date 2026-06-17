import { defineConfig } from "vitest/config";
import path from "node:path";
import { legacyEngineTests } from "./vitest.config";

// Runs ONLY the quarantined legacy TypeScript rules-engine tests (see vitest.config.ts).
// Kept so the suite can still be exercised on demand while it is excluded from the default gate.
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src")
    }
  },
  test: {
    environment: "node",
    include: legacyEngineTests
  }
});
