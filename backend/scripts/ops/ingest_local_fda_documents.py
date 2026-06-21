"""Batch-ingest the bundled local FDA documents listed in the local-documents manifest.

Run:  python -m scripts.ops.ingest_local_fda_documents"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.ops.ingest import ingest_source_pdf, ingest_source_xlsx


FINAL_RULE_PDF_URL = "https://www.govinfo.gov/content/pkg/FR-2022-11-21/pdf/2022-24417.pdf"


LOCAL_SOURCE_MAP = {
    "2022-24417-10.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417-2.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417-3.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417-4.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417-5.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417-6.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417-7.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417-8.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417-9.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "2022-24417.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "fr-2022-24417-final-rule.pdf": ("fr-2022-24417-final-rule-pdf", FINAL_RULE_PDF_URL),
    "fr-2023-technical-amendment.pdf": ("fr-2023-technical-amendment", "https://www.federalregister.gov/documents/2023/09/26/2023-20898/requirements-for-additional-traceability-records-for-certain-foods-technical-amendment"),
    "fr-2025-compliance-date-extension.pdf": ("fr-2025-compliance-date-extension-pdf", "https://www.federalregister.gov/documents/2025/08/07/2025-14967/requirements-for-additional-traceability-records-for-certain-foods-compliance-date-extension"),
    "fr-2026-cottage-cheese-exemption.pdf": ("fr-2026-cottage-cheese-exemption", "https://www.federalregister.gov/documents/2026/02/20/2026-03362/requirements-for-additional-traceability-records-for-certain-foods-exemption-for-cottage-cheeseunder"),
    "fda-public-meeting-2026.pdf": ("fda-public-meeting-2026", "https://www.federalregister.gov/documents/2026/05/28/2026-09537/challenges-and-solutions-in-lot-level-food-traceability-public-meeting-and-request-for-comments"),
    "fda-qa-guidance-2026.pdf": ("fda-qa-guidance-2026-pdf", "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-about-requirements-additional-traceability-records-certain-foods"),
    "fsma_traceability_qa-_draft_guidance_2023-520_-_clean_1-5-26.pdf": ("fda-qa-guidance-2026-pdf", "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-about-requirements-additional-traceability-records-certain-foods"),
    "fda-small-entity-guide-2023.pdf": ("fda-small-entity-guide-2023-pdf", "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/small-entity-compliance-guide-requirements-additional-traceability-records-certain-foods-what-you"),
    "FSMA Rule for Food Traceability - 2024-0520-CTEs-KDEs.pdf": ("fda-cte-kde-pdf", "https://www.fda.gov/media/163132/download?attachment"),
    "fda-lot-level-flexibility-discussion-paper.pdf": ("fda-lot-level-flexibility-discussion-paper", "https://www.fda.gov/media/192696/download?attachment"),
    "fda-tabletop-exercises-report.pdf": ("fda-tabletop-exercises-report", "https://www.fda.gov/media/192993/download?attachment"),
    "FSMAFoodTraceability-ElectronicSortableSpreadsheet-June2024.xlsx": ("fda-sortable-spreadsheet-xlsx", "https://www.fda.gov/media/179617/download?attachment"),
    "fsmafoodtraceability-electronicsortablespreadsheetwithsampledata-september2024.xlsx": ("fda-sortable-spreadsheet-sample-xlsx", "https://www.fda.gov/media/181946/download?attachment"),
    "TraceRule-TraceabilityPlanExampleforFarms-FactSheet-11202023.pdf": ("traceability-plan-farms", "https://www.fda.gov/media/174057/download?attachment"),
    "traceability-plan-farms.pdf": ("traceability-plan-farms", "https://www.fda.gov/media/174057/download?attachment"),
    "traceability-plan-restaurants.pdf": ("traceability-plan-restaurants", "https://www.fda.gov/media/174058/download?attachment"),
    "traceability-plan-sprouters.pdf": ("traceability-plan-sprouters", "https://www.fda.gov/media/181575/download?attachment"),
    "traceability-plan-food-processors.pdf": ("traceability-plan-food-processors", "https://www.fda.gov/media/188100/download?attachment"),
    "traceability-plan-distribution-centers.pdf": ("traceability-plan-distribution-centers", "https://www.fda.gov/media/188101/download?attachment"),
    "traceability-plan-seafood-processing.pdf": ("traceability-plan-seafood-processing", "https://www.fda.gov/media/188102/download?attachment"),
    "traceability-plan-aquaculture.pdf": ("traceability-plan-aquaculture", "https://www.fda.gov/media/188103/download?attachment"),
    "ecfr-21-cfr-1-subpart-s - 21 CFR Part 1 Subpart S (up to date as of 6-12-2026).pdf": ("ecfr-21-cfr-1-subpart-s-pdf", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-S"),
    "21 CFR 10.30 (up to date as of 6-12-2026).pdf": ("cfr-21-10-30", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-10/subpart-B/section-10.30"),
    "21 CFR 112.2 (up to date as of 6-12-2026).pdf": ("cfr-21-112-2", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-112/subpart-A/section-112.2"),
    "21 CFR 1240.60 (up to date as of 6-12-2026).pdf": ("cfr-21-1240-60", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-L/part-1240/subpart-D/section-1240.60"),
    "21 CFR 133.118 (up to date as of 6-12-2026).pdf": ("cfr-21-133-118", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-133/subpart-B/section-133.118"),
    "21 CFR 133.150 (up to date as of 6-12-2026).pdf": ("cfr-21-133-150", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-133/subpart-B/section-133.150"),
    "21 CFR Part 123 (up to date as of 6-12-2026).pdf": ("cfr-21-123", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-123"),
    "cfr-21-1-subpart-j.pdf": ("cfr-21-1-subpart-j", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-J"),
    "cfr-21-123-3.pdf": ("cfr-21-123-3", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-123/subpart-A/section-123.3"),
    "cfr-21-133-111": ("cfr-21-133-111", "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-133/subpart-B/section-133.111"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch ingest local FDA/CFR documents into Bellwether regulatory artifacts.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", default="../data/regulatory")
    parser.add_argument("--manifest", default="../data/regulatory/local-fda-documents-ingestion-manifest.json")
    parser.add_argument("--include-bellwether-context", action="store_true")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    manifest = []
    seen_hashes: set[str] = set()

    for path in sorted(input_dir.iterdir()):
        if path.name.startswith(".") or not path.is_file():
            continue
        mapped = LOCAL_SOURCE_MAP.get(path.name)
        if not mapped:
            mapped = (_slug(path.stem), f"local://{path.name}")
        source_id, url = mapped
        file_hash = _file_hash(path)
        duplicate = file_hash in seen_hashes
        seen_hashes.add(file_hash)
        if duplicate:
            manifest.append({"file": str(path), "sourceId": source_id, "url": url, "status": "duplicate_skipped"})
            continue
        source_output_dir = output_dir / source_id
        try:
            if _is_xlsx(path):
                result = ingest_source_xlsx(
                    xlsx_bytes=path.read_bytes(),
                    url=url,
                    source_id=source_id,
                    output_dir=source_output_dir,
                    include_trace_ready_context=args.include_bellwether_context,
                )
            else:
                result = ingest_source_pdf(
                    pdf_bytes=path.read_bytes(),
                    url=url,
                    source_id=source_id,
                    output_dir=source_output_dir,
                    include_trace_ready_context=args.include_bellwether_context,
                )
            manifest.append(
                {
                    "file": str(path),
                    "sourceId": source_id,
                    "url": url,
                    "status": "ingested",
                    "sectionsExtracted": result["sectionsExtracted"],
                    "chunks": len(result["chunks"]),
                    "rejectedChunks": len(result["rejectedChunks"]),
                    "normalizedArtifact": str(source_output_dir / "normalized" / f"{source_id}.json"),
                }
            )
        except Exception as error:
            manifest.append({"file": str(path), "sourceId": source_id, "url": url, "status": "failed", "error": str(error)})

    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"filesSeen": len(manifest), "ingested": sum(1 for item in manifest if item["status"] == "ingested"), "duplicatesSkipped": sum(1 for item in manifest if item["status"] == "duplicate_skipped"), "failed": sum(1 for item in manifest if item["status"] == "failed"), "manifest": str(manifest_path)}, indent=2))


def _is_xlsx(path: Path) -> bool:
    return path.suffix.lower() in {".xlsx", ".xlsm"}


def _file_hash(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value.lower()))


if __name__ == "__main__":
    main()
