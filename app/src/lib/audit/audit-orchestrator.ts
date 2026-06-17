import { evaluateReadinessGate } from "@/lib/regulatory/readiness-gate";
import { assertProposedRulesAreNotFinal } from "@/lib/regulatory/source-authority";
import { evaluateCteKdeCompleteness } from "@/lib/rules/cte-kde-completeness";
import { evaluateEntityScope, evaluateProductScope } from "@/lib/rules/scope-evaluators";
import { evaluateExemptionClaims } from "@/lib/rules/exemption-evaluator";
import { evaluateTraceabilityPlan } from "@/lib/rules/traceability-plan";
import { evaluateTlcAssignment } from "@/lib/rules/tlc-assignment";
import { evaluateTlcPreservation } from "@/lib/rules/tlc-preservation";
import { evaluateTlcLineage } from "@/lib/rules/tlc-lineage";
import { evaluateRecordsAvailability } from "@/lib/rules/records-availability";
import { evaluateAnomalies } from "@/lib/rules/anomaly-checks";
import { evaluateConsistencyChecks } from "@/lib/rules/consistency-checks";
import type { AuditContext } from "./audit-context";

export function runAudit(context: AuditContext) {
  const sourceErrors = assertProposedRulesAreNotFinal(context.sources);
  const findings = [
    ...evaluateEntityScope(context.dataset, context.ruleCards),
    ...evaluateProductScope(context.dataset, context.ruleCards),
    ...evaluateExemptionClaims(context.dataset, context.ruleCards),
    ...evaluateTraceabilityPlan(context.dataset, context.ruleCards),
    ...evaluateCteKdeCompleteness(context.dataset, context.kdeRequirements, context.ruleCards),
    ...evaluateTlcAssignment(context.dataset, context.ruleCards),
    ...evaluateTlcPreservation(context.dataset, context.ruleCards),
    ...evaluateTlcLineage(context.dataset, context.ruleCards),
    ...evaluateRecordsAvailability(context.dataset, context.ruleCards),
    ...evaluateConsistencyChecks(context.dataset, context.ruleCards),
    ...evaluateAnomalies(context.dataset, context.ruleCards)
  ];
  const readinessGate = evaluateReadinessGate({
    findings,
    ruleCards: context.ruleCards,
    chunks: context.chunks,
    kdeRequirements: context.kdeRequirements,
    scenarios: context.scenarios,
    obligations: context.obligations
  });

  return {
    mode: context.mode,
    sourceErrors,
    findings,
    readinessGate,
    coverage: buildCoverage(context, findings)
  };
}

function buildCoverage(context: AuditContext, findings: Array<{ findingType: string }>) {
  const requiredAreas = [
    "entity_scope",
    "product_scope",
    "exemptions",
    "traceability_plan",
    "harvest",
    "cooling",
    "initial_packing",
    "first_land_based_receiving",
    "shipping",
    "receiving",
    "transformation",
    "tlc_lineage",
    "records_availability"
  ];
  return requiredAreas.map((area) => {
    const hasRule = context.ruleCards.some((rule) => rule.ruleArea === area || rule.cteType === area);
    const hasFinding = findings.some((finding) => finding.findingType.includes(area));
    return {
      area,
      status: hasRule ? "ready" : "blocked",
      reason: hasRule ? (hasFinding ? "Evaluated with findings." : "Evaluated or not applicable.") : "Missing rule card."
    };
  });
}
