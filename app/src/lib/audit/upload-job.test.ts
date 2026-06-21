import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { auditUploadKey, createUploadAuditJob } from "./upload-job";
import type { QueuedUploadRecords, UploadAuditJobRepository } from "./upload-job";
import type { BellwetherSession } from "@/lib/auth/session";
import type { StorageProvider, StoredObject } from "@/lib/storage/storage-provider";

class CapturingStorage implements StorageProvider {
  objects: Array<{ key: string; bytes: Uint8Array; contentType: string }> = [];

  async put(key: string, bytes: Uint8Array, contentType: string): Promise<StoredObject> {
    this.objects.push({ key, bytes, contentType });
    return { bucket: "private-test-bucket", key, contentType, size: bytes.byteLength };
  }

  async get(key: string): Promise<Uint8Array | undefined> {
    return this.objects.find((object) => object.key === key)?.bytes;
  }
}

class CapturingRepository implements UploadAuditJobRepository {
  queued?: QueuedUploadRecords;

  async createQueuedUpload(input: QueuedUploadRecords): Promise<void> {
    this.queued = input;
  }
}

describe("upload audit job creation", () => {
  it("stores a workbook and prepares durable audit queue records", async () => {
    const storage = new CapturingStorage();
    const repository = new CapturingRepository();
    const bytes = new TextEncoder().encode("workbook bytes");

    const queued = await createUploadAuditJob(
      {
        fileName: "Distributor June Export.xlsx",
        bytes,
        contentType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        session: testSession()
      },
      { storage, repository }
    );

    expect(queued.auditProjectId).toMatch(/^audit_/);
    expect(queued.auditRunId).toMatch(/^run_/);
    expect(queued.auditFileId).toMatch(/^file_/);
    expect(queued.auditJobId).toMatch(/^job_/);
    expect(queued.storageBucket).toBe("private-test-bucket");
    expect(queued.storageKey).toContain(`/audits/${queued.auditProjectId}/runs/${queued.auditRunId}/uploads/Distributor-June-Export.xlsx`);
    expect(storage.objects).toHaveLength(1);

    const records = repository.queued;
    expect(records).toBeDefined();
    expect(records?.customer.name).toBe("Bellwether Pilot Co");
    expect(records?.membership.user_id).toBe(testSession().userId);
    expect(records?.auditProject.status).toBe("queued");
    expect(records?.auditProject.raw_workbook_key).toBe(queued.storageKey);
    expect(records?.auditRun.status).toBe("queued");
    expect(records?.auditRun.parser_version).toBe("customer_evidence_v1");
    expect(records?.auditRun.classifier_version).toBe("phase10c_multi_signal_v1");
    expect(records?.auditRun.rule_package_id).toBe("approved-rule-package-v1");
    expect(records?.auditFile.storage_bucket).toBe("private-test-bucket");
    expect(records?.auditFile.file_hash).toBe(createHash("sha256").update(bytes).digest("hex"));
    expect(records?.auditJob.job_type).toBe("parse_customer_workbook");
    expect(records?.auditJob.status).toBe("queued");
    expect(records?.auditJobEvent.event_type).toBe("upload_queued");
    expect(records?.auditJob.checkpoint_json).toMatchObject({
      stage: "queued",
      approvedRulePackageId: "approved-rule-package-v1",
      approvedRulePackageVersion: 1,
      storageBucket: "private-test-bucket",
      storageKey: queued.storageKey,
      originalFileName: "Distributor June Export.xlsx"
    });
  });

  it("sanitizes uploaded file names inside object-storage keys", () => {
    expect(
      auditUploadKey({
        customerId: "customer_123",
        auditProjectId: "audit_123",
        auditRunId: "run_123",
        fileName: "../lot export / june ?.xlsm"
      })
    ).toBe("customers/customer_123/audits/audit_123/runs/run_123/uploads/lot-export-june-.xlsm");
  });
});

function testSession(): BellwetherSession {
  return {
    userId: "11111111-1111-4111-8111-111111111111",
    email: "operator@example.com",
    fullName: "Pilot Operator",
    companyName: "Bellwether Pilot Co",
    role: "operator"
  };
}
