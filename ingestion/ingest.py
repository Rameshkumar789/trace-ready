from __future__ import annotations

import argparse
import json
from html import unescape
from pathlib import Path

from traceready_ingestion.chunking.legal_chunker import chunk_legal_meaning_with_rejections
from traceready_ingestion.context import build_source_context, classify_fsma_rule_entry
from traceready_ingestion.extractors.ecfr_xml_extractor import extract_ecfr_sections
from traceready_ingestion.extractors.fda_fsma_rules_page_extractor import (
    extract_fsma_rules_guidance_entries,
    extract_fsma_rules_guidance_sections,
)
from traceready_ingestion.extractors.html_extractor import extract_html_sections
from traceready_ingestion.extractors.pdf_extractor import build_semantic_pdf_sections, extract_pdf_pages
from traceready_ingestion.extractors.xlsx_extractor import extract_xlsx_sheets
from traceready_ingestion.fetchers.ecfr_fetcher import fetch_url
from traceready_ingestion.storage.artifacts import write_artifact
from traceready_ingestion.versioning.hashing import sha256_bytes, sha256_text


def ingest_source_text(
    *,
    text: str,
    url: str,
    source_id: str,
    output_dir: Path,
    raw_extension: str = "html",
    min_section: float | None = None,
    max_section: float | None = None,
    include_trace_ready_context: bool = False,
) -> dict:
    raw_key = write_artifact(output_dir / "raw", f"{source_id}.{raw_extension}", text)
    sections = extract_sections(text, min_section=min_section, max_section=max_section)
    source_hash = sha256_text(text)
    chunks, rejected_chunks = chunk_legal_meaning_with_rejections(
        source_id=source_id,
        source_url=url,
        source_hash=source_hash,
        retrieved_at="local-file",
        sections=sections,
    )
    normalized = {
        "sourceId": source_id,
        "url": url,
        "rawArtifact": raw_key,
        "rawTextHash": source_hash,
        "sectionsExtracted": len(sections),
        "chunks": [chunk.model_dump() for chunk in chunks],
        "rejectedChunks": [chunk.model_dump() for chunk in rejected_chunks],
    }
    fsma_entries = enrich_fsma_entries(text)
    if fsma_entries:
        normalized["fsmaRulesGuidanceEntries"] = fsma_entries
    if include_trace_ready_context:
        normalized["traceReadyContext"] = build_source_context(source_id, url)
    write_artifact(output_dir / "normalized", f"{source_id}.json", json.dumps(normalized, indent=2))
    return normalized


def ingest_source_pdf(
    *,
    pdf_bytes: bytes,
    url: str,
    source_id: str,
    output_dir: Path,
    include_trace_ready_context: bool = False,
) -> dict:
    raw_key = write_artifact(output_dir / "raw", f"{source_id}.pdf", pdf_bytes)
    source_hash = sha256_bytes(pdf_bytes)
    sections = extract_pdf_sections(pdf_bytes, source_id=source_id)
    chunks, rejected_chunks = chunk_legal_meaning_with_rejections(
        source_id=source_id,
        source_url=url,
        source_hash=source_hash,
        retrieved_at="local-file",
        sections=sections,
    )
    normalized = {
        "sourceId": source_id,
        "url": url,
        "rawArtifact": raw_key,
        "rawTextHash": source_hash,
        "contentType": "application/pdf",
        "sectionsExtracted": len(sections),
        "chunks": [chunk.model_dump() for chunk in chunks],
        "rejectedChunks": [chunk.model_dump() for chunk in rejected_chunks],
    }
    if include_trace_ready_context:
        normalized["traceReadyContext"] = build_source_context(source_id, url)
    write_artifact(output_dir / "normalized", f"{source_id}.json", json.dumps(normalized, indent=2))
    return normalized


def ingest_source_xlsx(
    *,
    xlsx_bytes: bytes,
    url: str,
    source_id: str,
    output_dir: Path,
    include_trace_ready_context: bool = False,
) -> dict:
    raw_key = write_artifact(output_dir / "raw", f"{source_id}.xlsx", xlsx_bytes)
    source_hash = sha256_bytes(xlsx_bytes)
    sections = extract_xlsx_sections(xlsx_bytes)
    chunks, rejected_chunks = chunk_legal_meaning_with_rejections(
        source_id=source_id,
        source_url=url,
        source_hash=source_hash,
        retrieved_at="local-file",
        sections=sections,
    )
    normalized = {
        "sourceId": source_id,
        "url": url,
        "rawArtifact": raw_key,
        "rawTextHash": source_hash,
        "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "sectionsExtracted": len(sections),
        "chunks": [chunk.model_dump() for chunk in chunks],
        "rejectedChunks": [chunk.model_dump() for chunk in rejected_chunks],
    }
    if include_trace_ready_context:
        normalized["traceReadyContext"] = build_source_context(source_id, url)
    write_artifact(output_dir / "normalized", f"{source_id}.json", json.dumps(normalized, indent=2))
    return normalized


def ingest_html_url(
    url: str,
    source_id: str,
    output_dir: Path,
    *,
    min_section: float | None = None,
    max_section: float | None = None,
    include_trace_ready_context: bool = False,
) -> dict:
    snapshot = fetch_url(url)
    is_pdf = "pdf" in snapshot.content_type.lower() or url.lower().split("?")[0].endswith(".pdf")
    is_xlsx = (
        "spreadsheet" in snapshot.content_type.lower()
        or "excel" in snapshot.content_type.lower()
        or url.lower().split("?")[0].endswith((".xlsx", ".xlsm"))
        or snapshot.body[:2] == b"PK"
    )
    raw_extension = "pdf" if is_pdf else "xlsx" if is_xlsx else "html"
    raw_content = snapshot.body if is_pdf or is_xlsx else snapshot.text
    source_hash = sha256_bytes(snapshot.body) if is_pdf or is_xlsx else sha256_text(snapshot.text)
    raw_key = write_artifact(output_dir / "raw", f"{source_id}.{raw_extension}", raw_content)
    sections = (
        extract_pdf_sections(snapshot.body, source_id=source_id)
        if is_pdf
        else extract_xlsx_sections(snapshot.body)
        if is_xlsx
        else extract_sections(snapshot.text, min_section=min_section, max_section=max_section)
    )
    chunks, rejected_chunks = chunk_legal_meaning_with_rejections(
        source_id=source_id,
        source_url=url,
        source_hash=source_hash,
        retrieved_at=snapshot.retrieved_at,
        sections=sections,
    )
    normalized = {
        "sourceId": source_id,
        "url": url,
        "rawArtifact": raw_key,
        "rawTextHash": source_hash,
        "contentType": snapshot.content_type,
        "sectionsExtracted": len(sections),
        "chunks": [chunk.model_dump() for chunk in chunks],
        "rejectedChunks": [chunk.model_dump() for chunk in rejected_chunks],
    }
    fsma_entries = enrich_fsma_entries(snapshot.text)
    if fsma_entries:
        normalized["fsmaRulesGuidanceEntries"] = fsma_entries
    if include_trace_ready_context:
        normalized["traceReadyContext"] = build_source_context(source_id, url)
    write_artifact(output_dir / "normalized", f"{source_id}.json", json.dumps(normalized, indent=2))
    return normalized


def extract_pdf_sections(pdf_bytes: bytes, *, source_id: str = "") -> list[dict]:
    return build_semantic_pdf_sections(extract_pdf_pages(pdf_bytes, source_id=source_id), source_id=source_id)


def extract_xlsx_sections(xlsx_bytes: bytes) -> list[dict]:
    sections = []
    for sheet in extract_xlsx_sheets(xlsx_bytes):
        text = sheet.get("text", "").strip()
        if not text:
            continue
        sheet_name = sheet.get("sheet", "sheet")
        sections.append(
            {
                "section_label": f"Workbook sheet: {sheet_name}",
                "section": str(sheet_name),
                "text": text,
            }
        )
    return sections


def extract_sections(text: str, *, min_section: float | None = None, max_section: float | None = None) -> list[dict]:
    if "<DIV8" in text and "TYPE=\"SECTION\"" in text:
        return extract_ecfr_sections(text, min_section=min_section, max_section=max_section)
    if is_fsma_rules_guidance_page(text):
        return extract_fsma_rules_guidance_sections(text)
    return extract_html_sections(text)


def enrich_fsma_entries(text: str) -> list[dict]:
    if not is_fsma_rules_guidance_page(text):
        return []
    entries = []
    for entry in extract_fsma_rules_guidance_entries(text):
        entries.append({**entry, "trace_ready_context": classify_fsma_rule_entry(entry["title"], entry.get("docket"))})
    return entries


def is_fsma_rules_guidance_page(text: str) -> bool:
    normalized = unescape(text).lower()
    return (
        "fsma rules & guidance for industry" in normalized
        and "guidance for industry & others" in normalized
        and "customtable" in normalized
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest an official FSMA regulatory source.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--input-file")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output-dir", default="../data/regulatory")
    parser.add_argument("--min-section", type=float)
    parser.add_argument("--max-section", type=float)
    parser.add_argument("--include-traceready-context", action="store_true")
    args = parser.parse_args()
    if args.input_file:
        source_path = Path(args.input_file)
        if source_path.suffix.lower() == ".pdf":
            result = ingest_source_pdf(
                pdf_bytes=source_path.read_bytes(),
                url=args.url,
                source_id=args.source_id,
                output_dir=Path(args.output_dir),
                include_trace_ready_context=args.include_traceready_context,
            )
        elif source_path.suffix.lower() in {".xlsx", ".xlsm"}:
            result = ingest_source_xlsx(
                xlsx_bytes=source_path.read_bytes(),
                url=args.url,
                source_id=args.source_id,
                output_dir=Path(args.output_dir),
                include_trace_ready_context=args.include_traceready_context,
            )
        else:
            result = ingest_source_text(
                text=source_path.read_text(errors="replace"),
                url=args.url,
                source_id=args.source_id,
                output_dir=Path(args.output_dir),
                raw_extension=source_path.suffix.lstrip(".") or "txt",
                min_section=args.min_section,
                max_section=args.max_section,
                include_trace_ready_context=args.include_traceready_context,
            )
    else:
        result = ingest_html_url(
            args.url,
            args.source_id,
            Path(args.output_dir),
            min_section=args.min_section,
            max_section=args.max_section,
            include_trace_ready_context=args.include_traceready_context,
        )
    print(
        json.dumps(
            {
                "sourceId": result["sourceId"],
                "sectionsExtracted": result["sectionsExtracted"],
                "chunks": len(result["chunks"]),
                "rejectedChunks": len(result["rejectedChunks"]),
                "traceReadyContextIncluded": "traceReadyContext" in result,
                "fsmaRulesGuidanceEntries": len(result.get("fsmaRulesGuidanceEntries", [])),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
