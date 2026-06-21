import { describe, expect, it, vi } from "vitest";
import { PrismaAuditRepository, createPrismaRepositories } from "./prisma-repositories";
import type { QueuedUploadRecords } from "@/lib/audit/upload-job";

describe("Prisma repositories", () => {
  it("maps queued upload records into a single Prisma transaction", async () => {
    const client = fakePrismaClient();
    const repository = new PrismaAuditRepository(client as never);

    await repository.createQueuedUpload(testQueuedUpload());

    expect(client.$transaction).toHaveBeenCalledOnce();
    expect(client.customer.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: "customer_1" },
        create: expect.objectContaining({ id: "customer_1", name: "Bellwether Pilot Co" })
      })
    );
    expect(client.customerMembership.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { customerId_userId: { customerId: "customer_1", userId: "11111111-1111-4111-8111-111111111111" } }
      })
    );
    expect(client.auditProject.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          id: "audit_1",
          customerId: "customer_1",
          rawWorkbookKey: "customers/customer_1/audits/audit_1/runs/run_1/uploads/records.xlsx"
        })
      })
    );
    expect(client.auditJob.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          id: "job_1",
          jobType: "parse_customer_workbook",
          checkpointJson: expect.objectContaining({ stage: "queued" })
        })
      })
    );
  });

  it("builds the enterprise repository bundle", () => {
    const repositories = createPrismaRepositories(fakePrismaClient() as never);

    expect(repositories.audits).toBeDefined();
    expect(repositories.auditJobs).toBeDefined();
    expect(repositories.auditArtifacts).toBeDefined();
    expect(repositories.regulatory).toBeDefined();
  });
});

function fakePrismaClient() {
  const operation = (name: string) => ({ name });
  return {
    $transaction: vi.fn(async (operations: unknown[]) => operations),
    customer: { upsert: vi.fn(() => operation("customer.upsert")) },
    customerMembership: { upsert: vi.fn(() => operation("customerMembership.upsert")) },
    auditProject: {
      create: vi.fn(() => operation("auditProject.create")),
      findUnique: vi.fn(async () => undefined),
      findMany: vi.fn(async () => [])
    },
    auditRun: { create: vi.fn(() => operation("auditRun.create")) },
    auditFile: { create: vi.fn(() => operation("auditFile.create")) },
    auditJob: { create: vi.fn(() => operation("auditJob.create")) },
    auditJobEvent: { create: vi.fn(() => operation("auditJobEvent.create")) },
    auditArtifact: { findMany: vi.fn(async () => []) },
    regulatorySource: { findMany: vi.fn(async () => []) },
    approvedRulePackage: { findMany: vi.fn(async () => []) }
  };
}

function testQueuedUpload(): QueuedUploadRecords {
  return {
    customer: {
      id: "customer_1",
      name: "Bellwether Pilot Co",
      status: "active"
    },
    membership: {
      id: "membership_1",
      customer_id: "customer_1",
      user_id: "11111111-1111-4111-8111-111111111111",
      role: "operator",
      status: "active"
    },
    auditProject: {
      id: "audit_1",
      customer_id: "customer_1",
      customer_name: "Bellwether Pilot Co",
      file_name: "records.xlsx",
      mode: "draft",
      status: "queued",
      created_by_user_id: "11111111-1111-4111-8111-111111111111",
      raw_workbook_key: "customers/customer_1/audits/audit_1/runs/run_1/uploads/records.xlsx",
      metadata_json: { uploadPipeline: "python_job" }
    },
    auditRun: {
      id: "run_1",
      audit_project_id: "audit_1",
      run_number: 1,
      status: "queued",
      mode: "draft",
      parser_version: "customer_evidence_v1",
      classifier_version: "phase10c_multi_signal_v1",
      rule_package_id: "approved-rule-package-v1",
      rule_package_version: 1,
      model_policy_json: { aiParsingAllowed: false },
      summary_json: { readinessStatus: "queued" }
    },
    auditFile: {
      id: "file_1",
      audit_project_id: "audit_1",
      audit_run_id: "run_1",
      file_name: "records.xlsx",
      file_type: "customer_workbook",
      content_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      storage_bucket: "private",
      storage_key: "customers/customer_1/audits/audit_1/runs/run_1/uploads/records.xlsx",
      file_hash: "hash",
      size_bytes: 123,
      uploaded_by_user_id: "11111111-1111-4111-8111-111111111111",
      status: "uploaded",
      metadata_json: { originalFileName: "records.xlsx" }
    },
    auditJob: {
      id: "job_1",
      audit_project_id: "audit_1",
      audit_run_id: "run_1",
      audit_file_id: "file_1",
      job_type: "parse_customer_workbook",
      status: "queued",
      priority: 100,
      max_attempts: 3,
      checkpoint_json: { stage: "queued" }
    },
    auditJobEvent: {
      audit_job_id: "job_1",
      audit_project_id: "audit_1",
      audit_run_id: "run_1",
      event_type: "upload_queued",
      message: "Customer workbook uploaded and queued for Python parsing.",
      payload_json: { stage: "queued" }
    }
  };
}
