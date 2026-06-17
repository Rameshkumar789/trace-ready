import type { CitationAnchor, RegulatorySource } from "./types";

export interface CitationAnchorInput {
  source: RegulatorySource;
  section?: string;
  paragraph?: string;
  tableLabel?: string;
  pageNumber?: number;
}

export function buildCitationAnchor(input: CitationAnchorInput): CitationAnchor {
  const citationParts = [input.source.citation, input.section, input.paragraph, input.tableLabel].filter(Boolean);
  return {
    sourceId: input.source.sourceId,
    citation: citationParts.join(" "),
    section: input.section,
    paragraph: input.paragraph,
    tableLabel: input.tableLabel,
    pageNumber: input.pageNumber,
    url: input.source.url,
    retrievedAt: input.source.retrievedAt,
    sourceHash: input.source.textHash
  };
}

export function anchorToDisplayCitation(anchor: CitationAnchor) {
  return [anchor.citation, anchor.pageNumber ? `p. ${anchor.pageNumber}` : undefined].filter(Boolean).join(", ");
}
