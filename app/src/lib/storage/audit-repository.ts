import type { StoredAudit } from "@/lib/audit/stored-audit";
import { PrismaStoredAuditRepository } from "./prisma-audit-repository";
import { loadAudit, saveAudit } from "./local-audit-store";

export interface AuditRepository {
  save(audit: StoredAudit): Promise<void>;
  load(auditId: string): Promise<StoredAudit | undefined>;
}

export class LocalAuditRepository implements AuditRepository {
  async save(audit: StoredAudit) {
    await saveAudit(audit);
  }

  async load(auditId: string) {
    return loadAudit(auditId);
  }
}

export function getAuditRepository(): AuditRepository {
  if (isProductionRuntime()) {
    if (process.env.TRACEREADY_ALLOW_LOCAL_AUDIT_STORE === "true") return new LocalAuditRepository();
    return new PrismaStoredAuditRepository();
  }
  return new LocalAuditRepository();
}

function isProductionRuntime() {
  return process.env.NODE_ENV === "production" || process.env.VERCEL_ENV === "production" || process.env.TRACEREADY_ENV === "production";
}
