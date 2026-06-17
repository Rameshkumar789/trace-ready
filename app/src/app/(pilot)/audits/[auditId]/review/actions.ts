"use server";

import { redirect } from "next/navigation";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import {
  applyCustomerFindingReviewAction,
  createCustomerReviewerOverride,
  promoteCustomerReviewerOverride
} from "@/lib/audit/customer-review-db";

export async function reviewFindingAction(formData: FormData) {
  const auditId = requiredText(formData, "auditId");
  const findingId = requiredText(formData, "findingId");
  const action = requiredText(formData, "action") as "approve" | "reject" | "edit" | "assign" | "comment" | "request_more_evidence";
  const reason = requiredText(formData, "reason");
  const comment = optionalText(formData, "comment");
  const assignedRole = optionalText(formData, "assignedRole");
  const session = await reviewerSession(`/audits/${auditId}/review`);
  await applyCustomerFindingReviewAction({
    auditId,
    findingId,
    action,
    reason,
    comment,
    assignedRole,
    session
  });
  redirect(`/audits/${auditId}/review?finding=${encodeURIComponent(findingId)}`);
}

export async function overrideFindingAction(formData: FormData) {
  const auditId = requiredText(formData, "auditId");
  const findingId = requiredText(formData, "findingId");
  const reason = requiredText(formData, "reason");
  const session = await reviewerSession(`/audits/${auditId}/review`);
  await createCustomerReviewerOverride({ auditId, findingId, reason, session });
  redirect(`/audits/${auditId}/review?finding=${encodeURIComponent(findingId)}`);
}

export async function promoteOverrideAction(formData: FormData) {
  const auditId = requiredText(formData, "auditId");
  const overrideId = requiredText(formData, "overrideId");
  const reason = requiredText(formData, "reason");
  const session = await reviewerSession(`/audits/${auditId}/review`);
  await promoteCustomerReviewerOverride({ auditId, overrideId, reason, session });
  redirect(`/audits/${auditId}/review`);
}

async function reviewerSession(nextPath: string) {
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, nextPath)) {
    redirect(`/login/reviewer?auth=required&next=${encodeURIComponent(nextPath)}`);
  }
  if (nextPath.includes("/demo/")) {
    throw new Error("Demo audit review actions are read-only. Upload a workbook to persist reviewer actions.");
  }
  return session;
}

function requiredText(formData: FormData, key: string) {
  const value = formData.get(key);
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${key} is required.`);
  }
  return value.trim();
}

function optionalText(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}
