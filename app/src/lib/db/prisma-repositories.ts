import type { Prisma } from "@prisma/client";
import type { QueuedUploadRecords } from "@/lib/audit/upload-job";
import { getPrismaClient, type TraceReadyPrismaClient } from "@/lib/db/prisma";
import type {
  AuditArtifactDbRepository,
  AuditDbRepository,
  AuditJobDbRepository,
  RegulatoryDbRepository,
  TraceReadyDbRepositories
} from "@/lib/db/repository-contracts";

type PrismaRepositoryClient = Pick<TraceReadyPrismaClient, "$transaction"> & {
  customer: Pick<TraceReadyPrismaClient["customer"], "upsert">;
  customerMembership: Pick<TraceReadyPrismaClient["customerMembership"], "upsert">;
  auditProject: Pick<TraceReadyPrismaClient["auditProject"], "create" | "findUnique" | "findMany">;
  auditRun: Pick<TraceReadyPrismaClient["auditRun"], "create">;
  auditFile: Pick<TraceReadyPrismaClient["auditFile"], "create">;
  auditJob: Pick<TraceReadyPrismaClient["auditJob"], "create">;
  auditJobEvent: Pick<TraceReadyPrismaClient["auditJobEvent"], "create">;
  auditArtifact: Pick<TraceReadyPrismaClient["auditArtifact"], "findMany">;
  regulatorySource: Pick<TraceReadyPrismaClient["regulatorySource"], "findMany">;
  approvedRulePackage: Pick<TraceReadyPrismaClient["approvedRulePackage"], "findMany">;
};

export function createPrismaRepositories(client: PrismaRepositoryClient = getPrismaClient()): TraceReadyDbRepositories {
  return {
    audits: new PrismaAuditRepository(client),
    auditJobs: new PrismaAuditJobRepository(client),
    auditArtifacts: new PrismaAuditArtifactRepository(client),
    regulatory: new PrismaRegulatoryRepository(client)
  };
}

export class PrismaAuditRepository implements AuditDbRepository {
  constructor(private readonly client: PrismaRepositoryClient = getPrismaClient()) {}

  async createQueuedUpload(input: QueuedUploadRecords): Promise<void> {
    await this.client.$transaction([
      this.client.customer.upsert({
        where: { id: input.customer.id },
        update: {
          name: input.customer.name,
          status: input.customer.status
        },
        create: {
          id: input.customer.id,
          name: input.customer.name,
          status: input.customer.status
        }
      }),
      this.client.customerMembership.upsert({
        where: {
          customerId_userId: {
            customerId: input.membership.customer_id,
            userId: input.membership.user_id
          }
        },
        update: {
          role: input.membership.role,
          status: input.membership.status
        },
        create: {
          id: input.membership.id,
          customerId: input.membership.customer_id,
          userId: input.membership.user_id,
          role: input.membership.role,
          status: input.membership.status
        }
      }),
      this.client.auditProject.create({
        data: {
          id: input.auditProject.id,
          customerId: input.auditProject.customer_id,
          customerName: input.auditProject.customer_name,
          fileName: input.auditProject.file_name,
          mode: input.auditProject.mode,
          status: input.auditProject.status,
          createdByUserId: input.auditProject.created_by_user_id,
          rawWorkbookKey: input.auditProject.raw_workbook_key,
          metadataJson: json(input.auditProject.metadata_json)
        }
      }),
      this.client.auditRun.create({
        data: {
          id: input.auditRun.id,
          auditProjectId: input.auditRun.audit_project_id,
          runNumber: input.auditRun.run_number,
          status: input.auditRun.status,
          mode: input.auditRun.mode,
          parserVersion: input.auditRun.parser_version,
          classifierVersion: input.auditRun.classifier_version,
          rulePackageId: input.auditRun.rule_package_id,
          rulePackageVersion: input.auditRun.rule_package_version,
          rulePackageHash: input.auditRun.rule_package_hash,
          modelPolicyJson: json(input.auditRun.model_policy_json),
          summaryJson: json(input.auditRun.summary_json)
        }
      }),
      this.client.auditFile.create({
        data: {
          id: input.auditFile.id,
          auditProjectId: input.auditFile.audit_project_id,
          auditRunId: input.auditFile.audit_run_id,
          fileName: input.auditFile.file_name,
          fileType: input.auditFile.file_type,
          contentType: input.auditFile.content_type,
          storageBucket: input.auditFile.storage_bucket,
          storageKey: input.auditFile.storage_key,
          fileHash: input.auditFile.file_hash,
          sizeBytes: input.auditFile.size_bytes,
          uploadedByUserId: input.auditFile.uploaded_by_user_id,
          status: input.auditFile.status,
          metadataJson: json(input.auditFile.metadata_json)
        }
      }),
      this.client.auditJob.create({
        data: {
          id: input.auditJob.id,
          auditProjectId: input.auditJob.audit_project_id,
          auditRunId: input.auditJob.audit_run_id,
          auditFileId: input.auditJob.audit_file_id,
          jobType: input.auditJob.job_type,
          status: input.auditJob.status,
          priority: input.auditJob.priority,
          maxAttempts: input.auditJob.max_attempts,
          checkpointJson: json(input.auditJob.checkpoint_json)
        }
      }),
      this.client.auditJobEvent.create({
        data: {
          auditJobId: input.auditJobEvent.audit_job_id,
          auditProjectId: input.auditJobEvent.audit_project_id,
          auditRunId: input.auditJobEvent.audit_run_id,
          eventType: input.auditJobEvent.event_type,
          message: input.auditJobEvent.message,
          payloadJson: json(input.auditJobEvent.payload_json)
        }
      })
    ]);
  }

  async loadAuditProject(id: string): Promise<unknown | undefined> {
    const project = await this.client.auditProject.findUnique({ where: { id } });
    return project ?? undefined;
  }

  async listAuditProjectsForCustomer(customerId: string, limit = 50): Promise<unknown[]> {
    return this.client.auditProject.findMany({
      where: { customerId },
      orderBy: { createdAt: "desc" },
      take: limit
    });
  }
}

export class PrismaAuditJobRepository implements AuditJobDbRepository {
  constructor(private readonly client: PrismaRepositoryClient = getPrismaClient()) {}

  async appendJobEvent(input: {
    auditJobId: string;
    auditProjectId?: string;
    auditRunId?: string;
    eventType: string;
    message?: string;
    payloadJson?: Record<string, unknown>;
  }): Promise<unknown> {
    return this.client.auditJobEvent.create({
      data: {
        auditJobId: input.auditJobId,
        auditProjectId: input.auditProjectId,
        auditRunId: input.auditRunId,
        eventType: input.eventType,
        message: input.message,
        payloadJson: json(input.payloadJson)
      }
    });
  }
}

function json(value: Record<string, unknown> | undefined): Prisma.InputJsonValue | undefined {
  return value as Prisma.InputJsonValue | undefined;
}

export class PrismaAuditArtifactRepository implements AuditArtifactDbRepository {
  constructor(private readonly client: PrismaRepositoryClient = getPrismaClient()) {}

  async listAuditArtifacts(input: {
    auditProjectId: string;
    auditRunId?: string;
    artifactTypes?: string[];
  }): Promise<unknown[]> {
    return this.client.auditArtifact.findMany({
      where: {
        auditProjectId: input.auditProjectId,
        auditRunId: input.auditRunId,
        artifactType: input.artifactTypes ? { in: input.artifactTypes } : undefined
      },
      orderBy: { createdAt: "desc" }
    });
  }
}

export class PrismaRegulatoryRepository implements RegulatoryDbRepository {
  constructor(private readonly client: PrismaRepositoryClient = getPrismaClient()) {}

  async listRegulatorySources(limit = 100): Promise<unknown[]> {
    return this.client.regulatorySource.findMany({
      orderBy: { retrievedAt: "desc" },
      take: limit
    });
  }

  async listApprovedRulePackages(limit = 20): Promise<unknown[]> {
    return this.client.approvedRulePackage.findMany({
      orderBy: { approvedAt: "desc" },
      take: limit
    });
  }
}
