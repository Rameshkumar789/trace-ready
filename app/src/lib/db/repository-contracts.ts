import type { QueuedUploadRecords, UploadAuditJobRepository } from "@/lib/audit/upload-job";

export interface AuditDbRepository extends UploadAuditJobRepository {
  loadAuditProject(id: string): Promise<unknown | undefined>;
  listAuditProjectsForCustomer(customerId: string, limit?: number): Promise<unknown[]>;
}

export interface AuditJobDbRepository {
  appendJobEvent(input: {
    auditJobId: string;
    auditProjectId?: string;
    auditRunId?: string;
    eventType: string;
    message?: string;
    payloadJson?: Record<string, unknown>;
  }): Promise<unknown>;
}

export interface AuditArtifactDbRepository {
  listAuditArtifacts(input: {
    auditProjectId: string;
    auditRunId?: string;
    artifactTypes?: string[];
  }): Promise<unknown[]>;
}

export interface RegulatoryDbRepository {
  listRegulatorySources(limit?: number): Promise<unknown[]>;
  listApprovedRulePackages(limit?: number): Promise<unknown[]>;
}

export interface TraceReadyDbRepositories {
  audits: AuditDbRepository;
  auditJobs: AuditJobDbRepository;
  auditArtifacts: AuditArtifactDbRepository;
  regulatory: RegulatoryDbRepository;
}

export type { QueuedUploadRecords, UploadAuditJobRepository };
