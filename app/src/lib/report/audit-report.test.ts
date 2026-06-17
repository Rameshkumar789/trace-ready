import { describe, expect, it } from "vitest";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import { generateAuditReport } from "./audit-report";

describe("audit report", () => {
  it("generates a readiness report and avoids certification language", () => {
    const report = generateAuditReport(runDemoAudit());
    expect(report.markdown).toContain("readiness audit");
    expect(report.markdown.toLowerCase()).not.toContain("certified compliant");
    expect(report.markdown).toContain("Source Registry And Rule Versions");
    expect(report.markdown).toContain("Source-System Readiness");
    expect(report.markdown).toContain("Supplier Data Quality");
    expect(report.markdown).toContain("Imported And Multilingual Record Review");
  });
});
