export interface AuditAccessSubject {
  userId?: string;
  role?: string;
  customerIds?: string[];
}

export interface AuditAccessProject {
  createdByUserId?: string | null;
  customerId?: string | null;
}

export function canAccessAudit(subject: AuditAccessSubject | string | undefined, projectOrOwnerId: AuditAccessProject | string) {
  if (typeof projectOrOwnerId === "string") {
    const userId = typeof subject === "string" ? subject : subject?.userId;
    return Boolean(userId) && userId === projectOrOwnerId;
  }

  const userId = typeof subject === "string" ? subject : subject?.userId;
  const role = typeof subject === "string" ? undefined : subject?.role;
  const customerIds = typeof subject === "string" ? [] : subject?.customerIds ?? [];
  if (!userId) return false;
  if (role === "founder_admin") return true;
  if (projectOrOwnerId.createdByUserId === userId) return true;
  return Boolean(projectOrOwnerId.customerId && customerIds.includes(projectOrOwnerId.customerId));
}
