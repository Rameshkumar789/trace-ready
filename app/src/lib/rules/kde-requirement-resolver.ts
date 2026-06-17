import type { CTEType } from "@/lib/ontology/types";
import type { KdeRequirementRecord } from "@/lib/regulatory/types";

export function resolveKdeRequirements(requirements: KdeRequirementRecord[], cteType: CTEType) {
  return requirements.filter((requirement) => requirement.status === "approved" && requirement.cteType === cteType);
}
