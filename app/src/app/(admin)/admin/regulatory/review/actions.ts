"use server";

import { createHash, randomUUID } from "node:crypto";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getTraceReadySession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

interface DraftRow {
  id: string;
  collection: string;
  record_id: string;
  review_status: string;
  source_chunk_ids: unknown;
  payload: unknown;
}

interface ApprovedRecordRow {
  id: string;
  collection: string;
  record_id: string;
  version: number;
  source_chunk_ids: unknown;
  payload: unknown;
}

export async function approveRegulatoryDraftAction(formData: FormData) {
  const draftId = requiredText(formData, "draftId");
  const reason = requiredText(formData, "reason");
  const next = safeNextPath(optionalText(formData, "next") ?? "/admin/regulatory/review");
  const session = await regulatoryReviewerSession("/admin/regulatory/review");
  const client = createSupabaseAdminClient();
  const draft = await loadDraft(client, draftId);
  const beforeJson = { reviewStatus: draft.review_status };
  const version = await nextApprovedRecordVersion(client, draft.collection, draft.record_id);
  const approvedRecordId = `approved_${randomUUID().replace(/-/g, "")}`;
  await insertOrThrow(
    client.from("approved_regulatory_records").insert({
      id: approvedRecordId,
      draft_record_id: draft.id,
      collection: draft.collection,
      record_id: draft.record_id,
      version,
      approved_by: session.email,
      approval_reason: reason,
      source_chunk_ids: draft.source_chunk_ids,
      payload: draft.payload
    })
  );
  await updateOrThrow(client.from("regulatory_draft_records").update({ review_status: "approved" }).eq("id", draft.id));
  await appendReviewAction({
    draftRecordId: draft.id,
    approvedRecordId,
    action: "approve_draft",
    actor: session.email,
    actorRole: session.role,
    reason,
    beforeJson,
    afterJson: { reviewStatus: "approved", approvedRecordId, version }
  });
  revalidatePath("/admin/regulatory/review");
  revalidatePath("/admin/regulatory/drafts");
  revalidatePath("/reviewer");
  redirect(next);
}

export async function rejectRegulatoryDraftAction(formData: FormData) {
  const draftId = requiredText(formData, "draftId");
  const reason = requiredText(formData, "reason");
  const next = safeNextPath(optionalText(formData, "next") ?? "/admin/regulatory/review");
  const session = await regulatoryReviewerSession("/admin/regulatory/review");
  const client = createSupabaseAdminClient();
  const draft = await loadDraft(client, draftId);
  await updateOrThrow(client.from("regulatory_draft_records").update({ review_status: "rejected" }).eq("id", draft.id));
  await appendReviewAction({
    draftRecordId: draft.id,
    action: "reject_draft",
    actor: session.email,
    actorRole: session.role,
    reason,
    beforeJson: { reviewStatus: draft.review_status },
    afterJson: { reviewStatus: "rejected" }
  });
  revalidatePath("/admin/regulatory/review");
  revalidatePath("/admin/regulatory/drafts");
  revalidatePath("/reviewer");
  redirect(next);
}

export async function publishApprovedRulePackageAction(formData: FormData) {
  const reason = requiredText(formData, "reason");
  const session = await regulatoryReviewerSession("/admin/regulatory/coverage");
  const client = createSupabaseAdminClient();
  const approvedRecords = await selectMany<ApprovedRecordRow>(
    client
      .from("approved_regulatory_records")
      .select("id, collection, record_id, version, source_chunk_ids, payload")
      .order("collection", { ascending: true })
      .order("record_id", { ascending: true })
  );
  if (!approvedRecords.length) throw new Error("Cannot publish an empty approved rule package.");
  const version = await nextPackageVersion(client, "approved-rule-package-v1");
  const packageId = `pkg_${randomUUID().replace(/-/g, "")}`;
  const packageHash = stableHash(approvedRecords.map((record) => ({ id: record.id, collection: record.collection, record_id: record.record_id, version: record.version, payload: record.payload })));
  const now = new Date().toISOString();
  await insertOrThrow(
    client.from("approved_rule_packages").insert({
      id: packageId,
      package_id: "approved-rule-package-v1",
      version,
      status: "approved",
      immutable: true,
      package_hash: packageHash,
      generated_at: now,
      approved_at: now,
      approved_by: session.email,
      approval_role: session.role,
      approval_reason: reason,
      scenario_gate_status: "not_run",
      metadata_json: {
        recordCount: approvedRecords.length,
        publicationSource: "regulatory_admin_action"
      }
    })
  );
  for (const record of approvedRecords) {
    await insertOrThrow(
      client.from("approved_rule_package_records").insert({
        approved_rule_package_id: packageId,
        collection: record.collection,
        record_id: record.record_id,
        record_version: record.version,
        approved_regulatory_record_id: record.id,
        payload: record.payload,
        source_chunk_ids: record.source_chunk_ids,
        record_hash: stableHash(record.payload)
      })
    );
  }
  revalidatePath("/admin/regulatory/coverage");
  revalidatePath("/admin/regulatory/versions");
  redirect("/admin/regulatory/versions");
}

async function regulatoryReviewerSession(nextPath: string) {
  const session = await getTraceReadySession();
  if (!session || !canAccessPath(session, nextPath)) {
    redirect(`/login/reviewer?auth=required&next=${encodeURIComponent(nextPath)}`);
  }
  return session;
}

async function loadDraft(client: ReturnType<typeof createSupabaseAdminClient>, draftId: string) {
  const draft = await selectMaybe<DraftRow>(
    client.from("regulatory_draft_records").select("id, collection, record_id, review_status, source_chunk_ids, payload").eq("id", draftId).maybeSingle()
  );
  if (!draft) throw new Error(`Draft not found: ${draftId}`);
  return draft;
}

async function nextApprovedRecordVersion(client: ReturnType<typeof createSupabaseAdminClient>, collection: string, recordId: string) {
  const latest = await selectMaybe<{ version: number }>(
    client
      .from("approved_regulatory_records")
      .select("version")
      .eq("collection", collection)
      .eq("record_id", recordId)
      .order("version", { ascending: false })
      .limit(1)
      .maybeSingle()
  );
  return (latest?.version ?? 0) + 1;
}

async function nextPackageVersion(client: ReturnType<typeof createSupabaseAdminClient>, packageId: string) {
  const latest = await selectMaybe<{ version: number }>(
    client
      .from("approved_rule_packages")
      .select("version")
      .eq("package_id", packageId)
      .order("version", { ascending: false })
      .limit(1)
      .maybeSingle()
  );
  return (latest?.version ?? 0) + 1;
}

async function appendReviewAction(input: {
  draftRecordId?: string;
  approvedRecordId?: string;
  action: string;
  actor: string;
  actorRole: string;
  reason: string;
  beforeJson: Record<string, unknown>;
  afterJson: Record<string, unknown>;
}) {
  await insertOrThrow(
    createSupabaseAdminClient().from("regulatory_review_actions").insert({
      id: `reg_review_${randomUUID().replace(/-/g, "")}`,
      draft_record_id: input.draftRecordId ?? null,
      approved_record_id: input.approvedRecordId ?? null,
      action: input.action,
      actor: input.actor,
      actor_role: input.actorRole,
      reason: input.reason,
      before_json: input.beforeJson,
      after_json: input.afterJson
    })
  );
}

function requiredText(formData: FormData, key: string) {
  const value = formData.get(key);
  if (typeof value !== "string" || !value.trim()) throw new Error(`${key} is required.`);
  return value.trim();
}

function optionalText(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function safeNextPath(value: string) {
  return value.startsWith("/") && !value.startsWith("//") ? value : "/admin/regulatory/review";
}

function stableHash(value: unknown) {
  return `sha256:${createHash("sha256").update(JSON.stringify(value)).digest("hex")}`;
}

async function selectMaybe<T>(operation: PromiseLike<{ data: unknown; error: { message: string } | null }>): Promise<T | undefined> {
  const { data, error } = await operation;
  if (error) throw new Error(error.message);
  return (data as T | null) ?? undefined;
}

async function selectMany<T>(operation: PromiseLike<{ data: unknown; error: { message: string } | null }>): Promise<T[]> {
  const { data, error } = await operation;
  if (error) throw new Error(error.message);
  return (data as T[] | null) ?? [];
}

async function insertOrThrow(operation: PromiseLike<{ error: { message: string } | null }>) {
  const { error } = await operation;
  if (error) throw new Error(error.message);
}

async function updateOrThrow(operation: PromiseLike<{ error: { message: string } | null }>) {
  const { error } = await operation;
  if (error) throw new Error(error.message);
}
