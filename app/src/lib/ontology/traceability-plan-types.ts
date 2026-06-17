import type { TraceabilityPlan } from "./types";

export function traceabilityPlanMissingItems(plan: TraceabilityPlan) {
  const missing: string[] = [];
  if (!plan.exists) missing.push("traceability_plan");
  if (!plan.recordMaintenanceProcedure) missing.push("record_maintenance_procedure");
  if (!plan.ftlIdentificationProcedure) missing.push("ftl_identification_procedure");
  if (!plan.pointOfContact) missing.push("point_of_contact");
  return missing;
}
