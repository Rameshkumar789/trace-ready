import fs from "node:fs";
import path from "node:path";
import type {
  KdeRequirementRecord,
  RegulatoryObligation,
  RegulatorySource,
  RuleCard,
  ScenarioCase,
  SourceChunk
} from "./types";

const appRoot = process.cwd();
const repoRoot = path.resolve(appRoot, "..");
const dataRoot = path.join(repoRoot, "data", "regulatory");

function readJson<T>(relativePath: string): T {
  const fullPath = path.join(dataRoot, relativePath);
  return JSON.parse(fs.readFileSync(fullPath, "utf8")) as T;
}

function readJsonIfExists<T>(relativePath: string, fallback: T): T {
  const fullPath = path.join(dataRoot, relativePath);
  if (!fs.existsSync(fullPath)) {
    return fallback;
  }
  return JSON.parse(fs.readFileSync(fullPath, "utf8")) as T;
}

export function loadRegulatorySources(): RegulatorySource[] {
  const sources = readJson<CanonicalSource[]>("registry/sources.json").map((source) => ({
    sourceId: source.source_id,
    title: source.title,
    sourceType: source.source_type,
    sourceStatus: sourceStatusFromCanonical(source),
    authorityRank: sourceAuthorityRankFromCanonical(source),
    url: source.url,
    citation: source.source_id,
    publishedDate: null,
    effectiveDate: source.effective_date,
    complianceDate: source.compliance_date,
    isFinalized: isFinalizedCanonicalSource(source),
    retrievedAt: source.retrieved_at,
    textHash: source.raw_hash,
    supersedes: [],
    supersededBy: [],
    notes: source.notes.join("; ")
  }));
  return [...sources, ...legacySourceAliases(sources)];
}

function loadSourceChunks(): SourceChunk[] {
  const chunks: SourceChunk[] = readJson<CanonicalSourceChunk[]>("registry/source-chunks.json").map((chunk) => ({
    chunkId: chunk.chunk_id,
    regulatorySourceId: chunk.source_id,
    chunkCode: chunk.chunk_id,
    sectionLabel: chunk.section_label,
    sourceLocation: chunk.section_ref ?? chunk.citation_anchor,
    text: chunk.text,
    summary: chunk.text.slice(0, 240),
    citation: chunk.citation_anchor,
    textHash: chunk.text_hash,
    status: "active" as const,
    authorityRank: chunk.authority_rank,
    isFinalizedSource: ["codified_rule", "final_rule", "guidance", "faq", "template", "scenario", "training"].includes(chunk.authority_rank),
    sourceUrl: chunk.source_url,
    anchors: [
      {
        sourceId: chunk.source_id,
        citation: chunk.citation_anchor,
        section: chunk.section_ref ?? undefined,
        pageNumber: chunk.page_number ?? undefined,
        url: chunk.source_url,
        sourceHash: chunk.text_hash
      }
    ]
  }));
  return [...chunks, ...legacyChunkAliases(chunks)];
}

function loadRuleCards(): RuleCard[] {
  return readJsonIfExists<RuleCard[]>("intelligence/review/phase6-approved-records.json", []);
}

function loadKdeRequirements(): KdeRequirementRecord[] {
  const files = [
    "kde-requirements/harvest-cooling.json",
    "kde-requirements/initial-packing.json",
    "kde-requirements/first-land-based-receiving.json",
    "kde-requirements/shipping.json",
    "kde-requirements/receiving.json",
    "kde-requirements/transformation.json",
    "kde-requirements/traceability-plan.json"
  ];
  return files.flatMap((file) => readJsonIfExists<KdeRequirementRecord[]>(file, []));
}

function loadScenarioCases(): ScenarioCase[] {
  return [
    ...readJsonIfExists<ScenarioCase[]>("scenarios/fsma204-core.json", []),
    ...readJsonIfExists<ScenarioCase[]>("scenarios/fsma204-expanded.json", [])
  ];
}

function loadObligations(): RegulatoryObligation[] {
  return readJsonIfExists<RegulatoryObligation[]>("obligations.json", []);
}

export function loadRegulatoryBundle() {
  return {
    sources: loadRegulatorySources(),
    chunks: loadSourceChunks(),
    ruleCards: loadRuleCards(),
    kdeRequirements: loadKdeRequirements(),
    scenarios: loadScenarioCases(),
    obligations: loadObligations()
  };
}

interface CanonicalSource {
  source_id: string;
  title: string;
  url: string;
  source_type: string;
  authority_rank: string;
  source_status: "ingested";
  effective_date: string | null;
  compliance_date: string | null;
  retrieved_at: string;
  raw_hash: string;
  notes: string[];
}

interface CanonicalSourceChunk {
  chunk_id: string;
  source_id: string;
  section_label: string;
  section_ref: string | null;
  page_number: number | null;
  text: string;
  text_hash: string;
  citation_anchor: string;
  authority_rank: string;
  source_url: string;
}

function sourceStatusFromCanonical(source: CanonicalSource): RegulatorySource["sourceStatus"] {
  if (source.source_id.includes("2025-compliance-date-extension")) {
    return "proposed_rule";
  }
  if (source.source_id.includes("discussion-paper")) {
    return "discussion_paper";
  }
  if (source.source_id.includes("faq")) {
    return "faq";
  }
  if (source.authority_rank === "federal_register_notice") {
    return "final_rule";
  }
  return source.authority_rank as RegulatorySource["sourceStatus"];
}

function sourceAuthorityRankFromCanonical(source: CanonicalSource): string {
  if (source.source_id.includes("2025-compliance-date-extension")) {
    return "proposed_rule";
  }
  if (source.source_id.includes("discussion-paper")) {
    return "discussion_paper";
  }
  return source.authority_rank;
}

function isFinalizedCanonicalSource(source: CanonicalSource): boolean {
  if (source.source_id.includes("2025-compliance-date-extension") || source.source_id.includes("discussion-paper")) {
    return false;
  }
  return ["codified_rule", "final_rule", "federal_register_notice", "guidance", "faq", "template", "scenario", "training"].includes(
    source.authority_rank
  );
}

function legacySourceAliases(sources: RegulatorySource[]): RegulatorySource[] {
  const aliases: Array<[string, string]> = [
    ["src-ecfr-subpart-s-current", "ecfr-21-cfr-1-subpart-s"],
    ["src-fda-faq", "fda-faq-food-traceability-rule"],
    ["src-fr-2025-proposed-extension", "fr-2025-compliance-date-extension-pdf"]
  ];
  return aliases.flatMap(([aliasId, sourceId]) => {
    const source = sources.find((candidate) => candidate.sourceId === sourceId);
    return source ? [{ ...source, sourceId: aliasId }] : [];
  });
}

function legacyChunkAliases(chunks: SourceChunk[]): SourceChunk[] {
  const aliases: Array<[string, string]> = [
    ["chunk-harvest-cooling-1325", "21 CFR 1.1325"],
    ["chunk-initial-packing-1330", "21 CFR 1.1330"],
    ["chunk-first-land-based-receiving-1335", "21 CFR 1.1335"],
    ["chunk-shipping-1340", "21 CFR 1.1340"],
    ["chunk-receiving-1345", "21 CFR 1.1345"],
    ["chunk-transformation-1350", "21 CFR 1.1350"]
  ];
  return aliases.flatMap(([aliasId, section]) => {
    const chunk = chunks.find((candidate) => candidate.regulatorySourceId === "ecfr-21-cfr-1-subpart-s" && candidate.sourceLocation === section);
    return chunk ? [{ ...chunk, chunkId: aliasId, chunkCode: aliasId }] : [];
  });
}
