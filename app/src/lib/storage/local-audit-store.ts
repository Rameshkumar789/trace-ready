import fs from "node:fs/promises";
import path from "node:path";
import type { StoredAudit, StoredAuditSummary } from "@/lib/audit/stored-audit";

const storeRoot = path.join(process.cwd(), "storage", "audits");

export function createAuditId(fileName: string) {
  const safeName = fileName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "audit";
  return `${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}-${safeName}`;
}

export async function saveAudit(audit: StoredAudit) {
  assertLocalAuditStoreAllowed();
  const dir = path.join(storeRoot, audit.auditId);
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(path.join(dir, "audit.json"), JSON.stringify(audit, null, 2));
}

export async function loadAudit(auditId: string): Promise<StoredAudit | undefined> {
  assertLocalAuditStoreAllowed();
  try {
    const content = await fs.readFile(path.join(storeRoot, auditId, "audit.json"), "utf8");
    return JSON.parse(content) as StoredAudit;
  } catch {
    return undefined;
  }
}

export async function listAudits(): Promise<StoredAuditSummary[]> {
  assertLocalAuditStoreAllowed();
  try {
    const entries = await fs.readdir(storeRoot, { withFileTypes: true });
    const audits = await Promise.all(
      entries
        .filter((entry) => entry.isDirectory())
        .map(async (entry) => {
          const audit = await loadAudit(entry.name);
          if (!audit) return undefined;
          return {
            auditId: audit.auditId,
            createdAt: audit.createdAt,
            fileName: audit.fileName,
            findingsCount: audit.findings.length,
            blockerCount: audit.readinessGate.blockers.length,
            mode: audit.mode,
            readinessPassed: audit.readinessGate.passed
          } satisfies StoredAuditSummary;
        })
    );

    return audits
      .filter((audit): audit is StoredAuditSummary => Boolean(audit))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  } catch {
    return [];
  }
}

function assertLocalAuditStoreAllowed() {
  if (isProductionRuntime() && process.env.TRACEREADY_ALLOW_LOCAL_AUDIT_STORE !== "true") {
    throw new Error("Local audit JSON storage is disabled in production. Use DB/object-storage repositories.");
  }
}

function isProductionRuntime() {
  return process.env.NODE_ENV === "production" || process.env.VERCEL_ENV === "production" || process.env.TRACEREADY_ENV === "production";
}
