import type { KDE, KDERequirement } from "./types";

export function kdeIsPresent(kde: KDE) {
  return kde.status === "present" && Boolean(kde.value?.trim());
}

export function requirementIsExecutable(requirement: KDERequirement) {
  return requirement.status === "approved" && Boolean(requirement.reviewedBy) && Boolean(requirement.reviewedAt);
}
