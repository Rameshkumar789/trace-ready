import type { NormalizedAuditDataset } from "@/lib/ontology/types";
import type {
  KdeRequirementRecord,
  RegulatoryObligation,
  RegulatorySource,
  RuleCard,
  ScenarioCase,
  SourceChunk
} from "@/lib/regulatory/types";

export interface AuditContext {
  mode: "draft" | "customer_facing";
  sources: RegulatorySource[];
  chunks: SourceChunk[];
  ruleCards: RuleCard[];
  kdeRequirements: KdeRequirementRecord[];
  scenarios: ScenarioCase[];
  obligations: RegulatoryObligation[];
  dataset: NormalizedAuditDataset;
}
