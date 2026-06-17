import { generateAuditReport } from "./audit-report";

export function exportAuditHtml(input: Parameters<typeof generateAuditReport>[0]) {
  const report = generateAuditReport(input);
  return `<!doctype html><html><head><meta charset="utf-8"><title>TraceReady Readiness Audit</title></head><body><pre>${escapeHtml(
    report.markdown
  )}</pre></body></html>`;
}

function escapeHtml(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
