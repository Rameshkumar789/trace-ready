import type { RegulatorySource } from "./types";

export function sortByAuthority(sources: RegulatorySource[]) {
  return [...sources].sort((a, b) => authorityRankValue(a.authorityRank) - authorityRankValue(b.authorityRank));
}

export function canOverride(lowerCandidate: RegulatorySource, current: RegulatorySource) {
  return authorityRankValue(lowerCandidate.authorityRank) <= authorityRankValue(current.authorityRank) && lowerCandidate.isFinalized;
}

export function assertProposedRulesAreNotFinal(sources: RegulatorySource[]) {
  const failures = sources.filter((source) => source.sourceStatus === "proposed_rule" && source.isFinalized);
  if (failures.length > 0) {
    return failures.map((source) => `${source.sourceId} is proposed_rule but finalized`);
  }
  return [];
}

export function sourceAuthoritySummary(sources: RegulatorySource[]) {
  return sortByAuthority(sources).map((source) => ({
    sourceId: source.sourceId,
    citation: source.citation,
    status: source.sourceStatus,
    rank: source.authorityRank,
    isFinalized: source.isFinalized
  }));
}

function authorityRankValue(rank: RegulatorySource["authorityRank"]) {
  if (typeof rank === "number") {
    return rank;
  }
  return (
    {
      codified_rule: 1,
      final_rule: 2,
      federal_register_notice: 3,
      guidance: 4,
      faq: 5,
      template: 6,
      cross_reference: 7,
      scenario: 8,
      training: 9,
      research: 9,
      support: 10,
      market_impact: 11,
      change_monitor: 12,
      proposed_rule: 13,
      discussion_paper: 14
    }[rank] ?? 99
  );
}
