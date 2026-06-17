import { createHash, randomUUID } from "node:crypto";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import type { TraceReadySession } from "@/lib/auth/session-cookie";
import type { StorageProvider, StoredObject } from "@/lib/storage/storage-provider";
import { getRequiredStorageProvider } from "@/lib/storage/supabase-storage";

const PARSER_VERSION = "customer_evidence_v1";
const CLASSIFIER_VERSION = "phase10c_multi_signal_v1";

export interface UploadAuditJobInput {
  fileName: string;
  bytes: Uint8Array;
  contentType: string;
  session: TraceReadySession;
}

export interface QueuedAuditJob {
  auditProjectId: string;
  auditRunId: string;
  auditFileId: string;
  auditJobId: string;
  customerId: string;
  storageBucket: string;
  storageKey: string;
}

export interface UploadAuditJobRepository {
  createQueuedUpload(input: QueuedUploadRecords): Promise<void>;
}

export interface QueuedUploadRecords {
  customer: {
    id: string;
    name: string;
    status: string;
  };
  membership: {
    id: string;
    customer_id: string;
    user_id: string;
    role: string;
    status: string;
  };
  auditProject: {
    id: string;
    customer_id: string;
    customer_name: string;
    file_name: string;
    mode: string;
    status: string;
    created_by_user_id: string;
    raw_workbook_key: string;
    metadata_json: Record<string, unknown>;
  };
  auditRun: {
    id: string;
    audit_project_id: string;
    run_number: number;
    status: string;
    mode: string;
    parser_version: string;
    classifier_version: string;
    rule_package_id: string;
    rule_package_version: number;
    rule_package_hash?: string;
    model_policy_json: Record<string, unknown>;
    summary_json: Record<string, unknown>;
  };
  auditFile: {
    id: string;
    audit_project_id: string;
    audit_run_id: string;
    file_name: string;
    file_type: string;
    content_type: string;
    storage_bucket: string;
    storage_key: string;
    file_hash: string;
    size_bytes: number;
    uploaded_by_user_id: string;
    status: string;
    metadata_json: Record<string, unknown>;
  };
  auditJob: {
    id: string;
    audit_project_id: string;
    audit_run_id: string;
    audit_file_id: string;
    job_type: string;
    status: string;
    priority: number;
    max_attempts: number;
    checkpoint_json: Record<string, unknown>;
  };
  auditJobEvent: {
    audit_job_id: string;
    audit_project_id: string;
    audit_run_id: string;
    event_type: string;
    message: string;
    payload_json: Record<string, unknown>;
  };
}

export class SupabaseUploadAuditJobRepository implements UploadAuditJobRepository {
  private client = createSupabaseAdminClient();

  async createQueuedUpload(input: QueuedUploadRecords): Promise<void> {
    await insertOrThrow(this.client.from("customers").upsert(input.customer, { onConflict: "id" }));
    await insertOrThrow(this.client.from("customer_memberships").upsert(input.membership, { onConflict: "customer_id,user_id" }));
    await insertOrThrow(this.client.from("audit_projects").insert(input.auditProject));
    await insertOrThrow(this.client.from("audit_runs").insert(input.auditRun));
    await insertOrThrow(this.client.from("audit_files").insert(input.auditFile));
    await insertOrThrow(this.client.from("audit_jobs").insert(input.auditJob));
    await insertOrThrow(this.client.from("audit_job_events").insert(input.auditJobEvent));
  }
}

export async function createUploadAuditJob(
  input: UploadAuditJobInput,
  dependencies: {
    storage?: StorageProvider;
    repository?: UploadAuditJobRepository;
  } = {}
): Promise<QueuedAuditJob> {
  const storage = dependencies.storage ?? getRequiredStorageProvider();
  const repository = dependencies.repository ?? await createDefaultUploadAuditJobRepository();
  const now = new Date().toISOString();
  const customer = customerFromSession(input.session);
  const auditProjectId = newId("audit");
  const auditRunId = newId("run");
  const auditFileId = newId("file");
  const auditJobId = newId("job");
  const fileHash = sha256(input.bytes);
  const storageKey = auditUploadKey({
    customerId: customer.id,
    auditProjectId,
    auditRunId,
    fileName: input.fileName
  });
  const stored = await storage.put(storageKey, input.bytes, input.contentType);
  const rulePackagePin = approvedRulePackagePin();

  await repository.createQueuedUpload(
    buildQueuedUploadRecords({
      input,
      customer,
      auditProjectId,
      auditRunId,
      auditFileId,
      auditJobId,
      stored,
      fileHash,
      now,
      rulePackagePin
    })
  );

  return {
    auditProjectId,
    auditRunId,
    auditFileId,
    auditJobId,
    customerId: customer.id,
    storageBucket: stored.bucket,
    storageKey: stored.key
  };
}

async function createDefaultUploadAuditJobRepository(): Promise<UploadAuditJobRepository> {
  if (!process.env.DATABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return new SupabaseUploadAuditJobRepository();
  }
  const { PrismaAuditRepository } = await import("@/lib/db/prisma-repositories");
  return new PrismaAuditRepository();
}

export function auditUploadKey({
  customerId,
  auditProjectId,
  auditRunId,
  fileName
}: {
  customerId: string;
  auditProjectId: string;
  auditRunId: string;
  fileName: string;
}) {
  return ["customers", customerId, "audits", auditProjectId, "runs", auditRunId, "uploads", safeObjectSegment(fileName)].join("/");
}

export function customerFromSession(session: TraceReadySession) {
  const companyName = session.companyName?.trim() || `${session.email} workspace`;
  return {
    id: `customer_${sha256Text(companyName.toLowerCase()).slice(0, 24)}`,
    name: companyName
  };
}

function buildQueuedUploadRecords({
  input,
  customer,
  auditProjectId,
  auditRunId,
  auditFileId,
  auditJobId,
  stored,
  fileHash,
  now,
  rulePackagePin
}: {
  input: UploadAuditJobInput;
  customer: { id: string; name: string };
  auditProjectId: string;
  auditRunId: string;
  auditFileId: string;
  auditJobId: string;
  stored: StoredObject;
  fileHash: string;
  now: string;
  rulePackagePin: ReturnType<typeof approvedRulePackagePin>;
}): QueuedUploadRecords {
  const checkpoint = {
    stage: "queued",
    createdAt: now,
    parserVersion: PARSER_VERSION,
    classifierVersion: CLASSIFIER_VERSION,
    approvedRulePackageId: rulePackagePin.packageId,
    approvedRulePackageVersion: rulePackagePin.version,
    approvedRulePackageHash: rulePackagePin.hash,
    customerId: customer.id,
    auditFileId,
    storageBucket: stored.bucket,
    storageKey: stored.key,
    originalFileName: input.fileName
  };
  return {
    customer: {
      id: customer.id,
      name: customer.name,
      status: "active"
    },
    membership: {
      id: `membership_${sha256Text(`${customer.id}:${input.session.userId}`).slice(0, 24)}`,
      customer_id: customer.id,
      user_id: input.session.userId,
      role: input.session.role,
      status: "active"
    },
    auditProject: {
      id: auditProjectId,
      customer_id: customer.id,
      customer_name: customer.name,
      file_name: input.fileName,
      mode: "draft",
      status: "queued",
      created_by_user_id: input.session.userId,
      raw_workbook_key: stored.key,
      metadata_json: {
        uploadContentType: stored.contentType,
        uploadSizeBytes: stored.size,
        uploadSha256: fileHash,
        uploadedAt: now,
        uploadPipeline: "python_job"
      }
    },
    auditRun: {
      id: auditRunId,
      audit_project_id: auditProjectId,
      run_number: 1,
      status: "queued",
      mode: "draft",
      parser_version: PARSER_VERSION,
      classifier_version: CLASSIFIER_VERSION,
      rule_package_id: rulePackagePin.packageId,
      rule_package_version: rulePackagePin.version,
      rule_package_hash: rulePackagePin.hash,
      model_policy_json: {
        finalVerdicts: "deterministic_approved_rules_only",
        aiUsage: "drafting_and_mapping_assist_only"
      },
      summary_json: {
        status: "queued",
        uploadedAt: now,
        nextJobType: "parse_customer_workbook"
      }
    },
    auditFile: {
      id: auditFileId,
      audit_project_id: auditProjectId,
      audit_run_id: auditRunId,
      file_name: input.fileName,
      file_type: "customer_workbook",
      content_type: stored.contentType,
      storage_bucket: stored.bucket,
      storage_key: stored.key,
      file_hash: fileHash,
      size_bytes: stored.size,
      uploaded_by_user_id: input.session.userId,
      status: "uploaded",
      metadata_json: {
        originalFileName: input.fileName,
        uploadedAt: now
      }
    },
    auditJob: {
      id: auditJobId,
      audit_project_id: auditProjectId,
      audit_run_id: auditRunId,
      audit_file_id: auditFileId,
      job_type: "parse_customer_workbook",
      status: "queued",
      priority: 100,
      max_attempts: 3,
      checkpoint_json: checkpoint
    },
    auditJobEvent: {
      audit_job_id: auditJobId,
      audit_project_id: auditProjectId,
      audit_run_id: auditRunId,
      event_type: "upload_queued",
      message: "Customer workbook uploaded and queued for Python parsing.",
      payload_json: checkpoint
    }
  };
}

function approvedRulePackagePin() {
  return {
    packageId: process.env.TRACEREADY_APPROVED_RULE_PACKAGE_ID ?? "approved-rule-package-v1",
    version: Number.parseInt(process.env.TRACEREADY_APPROVED_RULE_PACKAGE_VERSION ?? "1", 10),
    hash: process.env.TRACEREADY_APPROVED_RULE_PACKAGE_HASH || undefined
  };
}

function newId(prefix: string) {
  return `${prefix}_${randomUUID().replace(/-/g, "")}`;
}

function safeObjectSegment(value: string) {
  return (
    value
      .trim()
      .replace(/[\\/]+/g, "-")
      .replace(/[^A-Za-z0-9._=-]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^\.+/g, "")
      .replace(/^-+|-+$/g, "") || "workbook.xlsx"
  );
}

function sha256(bytes: Uint8Array) {
  return createHash("sha256").update(bytes).digest("hex");
}

function sha256Text(value: string) {
  return createHash("sha256").update(value).digest("hex");
}

async function insertOrThrow(operation: PromiseLike<{ error: { message: string } | null }>) {
  const { error } = await operation;
  if (error) {
    throw new Error(error.message);
  }
}
