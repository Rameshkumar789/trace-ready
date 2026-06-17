import type { RegulatorySource, SourceChunk } from "./types";
import { buildCitationAnchor } from "./citation-anchor";

export interface LegalSection {
  sectionLabel: string;
  section: string;
  text: string;
  summary?: string;
  paragraph?: string;
  tableLabel?: string;
  pageNumber?: number;
}

export function chunkLegalMeaning(source: RegulatorySource, sections: LegalSection[]): SourceChunk[] {
  return sections.map((section, index) => {
    assertChunkKeepsObligationTogether(section.text);
    const anchor = buildCitationAnchor({
      source,
      section: section.section,
      paragraph: section.paragraph,
      tableLabel: section.tableLabel,
      pageNumber: section.pageNumber
    });
    return {
      chunkId: `${source.sourceId}-${slug(section.sectionLabel)}-${index + 1}`,
      regulatorySourceId: source.sourceId,
      chunkCode: `${slug(source.citation)}-${slug(section.section)}`,
      sectionLabel: section.sectionLabel,
      sourceLocation: section.section,
      text: section.text.trim(),
      summary: section.summary ?? summarize(section.text),
      citation: anchor.citation,
      textHash: stableChunkHash(source.textHash, section.text),
      status: "active",
      authorityRank: source.authorityRank,
      isFinalizedSource: source.isFinalized,
      retrievedAt: source.retrievedAt,
      sourceUrl: source.url,
      version: 1,
      anchors: [anchor]
    };
  });
}

export function assertChunkKeepsObligationTogether(text: string) {
  const normalized = text.toLowerCase();
  const hasCondition = /\b(if|when|unless|where|provided that)\b/.test(normalized);
  const hasObligation = /\b(must|shall|required|requires|maintain|keep|establish)\b/.test(normalized);
  if (hasCondition && !hasObligation) {
    throw new Error("Legal chunk has conditions without the corresponding obligation.");
  }
}

function summarize(text: string) {
  const clean = text.replace(/\s+/g, " ").trim();
  return clean.length <= 180 ? clean : `${clean.slice(0, 177)}...`;
}

function slug(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function stableChunkHash(sourceHash: string, text: string) {
  let hash = 0;
  for (const char of `${sourceHash}:${text}`) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return `sha256:${hash.toString(16).padStart(8, "0")}`;
}
