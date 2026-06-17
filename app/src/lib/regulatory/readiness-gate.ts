import type { Finding } from "@/lib/findings/finding";
import type { KdeRequirementRecord, RegulatoryObligation, RuleCard, ScenarioCase, SourceChunk } from "./types";
import { validateRuleCard } from "./validate-rule-card";

export interface ReadinessGateResult {
  passed: boolean;
  blockers: string[];
}

export function evaluateReadinessGate(input: {
  findings: Finding[];
  ruleCards: RuleCard[];
  chunks: SourceChunk[];
  kdeRequirements: KdeRequirementRecord[];
  scenarios: ScenarioCase[];
  obligations?: RegulatoryObligation[];
}): ReadinessGateResult {
  const blockers: string[] = [];
  blockers.push(...evaluateObligationCoverage(input.obligations ?? [], input.ruleCards, input.kdeRequirements, input.chunks));

  for (const finding of input.findings) {
    if (finding.status === "pass" || finding.status === "not_applicable") continue;
    const ruleCard = input.ruleCards.find((card) => card.ruleCardId === finding.ruleCardId);
    if (!ruleCard) {
      blockers.push(`${finding.findingId}: missing approved rule card`);
      continue;
    }
    const ruleValidation = validateRuleCard(ruleCard, input.chunks, true);
    blockers.push(...ruleValidation.errors.map((error) => `${finding.findingId}: ${error}`));

    const hasScenario = input.scenarios.some(
      (scenario) => scenario.status === "approved" && scenario.linkedRuleCardIds.includes(ruleCard.ruleCardId)
    );
    if (!hasScenario) blockers.push(`${finding.findingId}: rule card has no approved scenario coverage`);
    if (!finding.sourceChunkId) blockers.push(`${finding.findingId}: missing source chunk reference`);
    if (!finding.evidenceRefs.length) blockers.push(`${finding.findingId}: missing evidence mapping`);
    if (!finding.reviewState) blockers.push(`${finding.findingId}: missing human review state`);
    if (finding.reviewState !== "approved") {
      blockers.push(`${finding.findingId}: customer-facing output requires approved human review`);
    }
    if (finding.kdeRequirementId) {
      const requirement = input.kdeRequirements.find((kde) => kde.kdeRequirementId === finding.kdeRequirementId);
      if (!requirement || requirement.status !== "approved") {
        blockers.push(`${finding.findingId}: missing approved KDE requirement`);
      }
    }
    if (!ruleCard.isFinalizedSource && !["proposed_change", "needs_expert_review"].includes(finding.status)) {
      blockers.push(`${finding.findingId}: proposed/non-final source cannot create final finding state`);
    }
  }

  return { passed: blockers.length === 0, blockers };
}

function evaluateObligationCoverage(
  obligations: RegulatoryObligation[],
  ruleCards: RuleCard[],
  kdeRequirements: KdeRequirementRecord[],
  chunks: SourceChunk[]
) {
  const blockers: string[] = [];
  if (!obligations.length) {
    blockers.push("source gate: obligation inventory is missing");
    return blockers;
  }
  for (const obligation of obligations.filter((item) => item.status === "approved")) {
    if (!obligation.sourceChunkIds.length) blockers.push(`${obligation.obligationId}: missing source chunk coverage`);
    if (!obligation.ruleCardIds.length) blockers.push(`${obligation.obligationId}: missing rule-card coverage`);
    for (const chunkId of obligation.sourceChunkIds) {
      const chunk = chunks.find((item) => item.chunkId === chunkId);
      if (!chunk || !chunk.citation || !chunk.textHash.startsWith("sha256:")) {
        blockers.push(`${obligation.obligationId}: source chunk ${chunkId} lacks citation/hash coverage`);
      }
    }
    for (const ruleCardId of obligation.ruleCardIds) {
      const ruleCard = ruleCards.find((item) => item.ruleCardId === ruleCardId);
      if (!ruleCard || ruleCard.status !== "approved") {
        blockers.push(`${obligation.obligationId}: rule card ${ruleCardId} is not approved`);
      }
    }
    for (const kdeRequirementId of obligation.kdeRequirementIds) {
      const requirement = kdeRequirements.find((item) => item.kdeRequirementId === kdeRequirementId);
      if (!requirement || requirement.status !== "approved") {
        blockers.push(`${obligation.obligationId}: KDE requirement ${kdeRequirementId} is not approved`);
      }
    }
  }
  return blockers;
}
