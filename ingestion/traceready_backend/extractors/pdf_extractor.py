from __future__ import annotations

import re
from io import BytesIO


def extract_pdf_pages(pdf_bytes: bytes, *, source_id: str = "") -> list[dict]:
    try:
        import pdfplumber  # type: ignore

        pages = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                if _needs_column_order(source_id):
                    text = _extract_column_ordered_text(page)
                    tables = []
                else:
                    text = page.extract_text() or ""
                    tables = page.extract_tables() or []
                table_text = _tables_to_text(tables)
                combined = "\n\n".join(part for part in [text, table_text] if part.strip()).strip()
                pages.append({"page": index, "text": combined})
        if any(page["text"].strip() for page in pages):
            return pages
    except Exception:
        pass

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(pdf_bytes))
        return [
            {"page": index, "text": page.extract_text() or ""}
            for index, page in enumerate(reader.pages, start=1)
        ]
    except Exception:
        pass

    try:
        import fitz  # type: ignore
    except Exception:
        return [{"page": 1, "text": pdf_bytes.decode("utf-8", errors="replace")}]

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [{"page": page.number + 1, "text": page.get_text("text")} for page in doc]


def _needs_column_order(source_id: str) -> bool:
    source_key = source_id.lower()
    return source_key.startswith("fr-") or "federal-register" in source_key


def _extract_column_ordered_text(page) -> str:
    words = page.extract_words(
        x_tolerance=2,
        y_tolerance=3,
        keep_blank_chars=False,
        use_text_flow=False,
    )
    if not words:
        return page.extract_text() or ""

    height = float(getattr(page, "height", 0) or 0)
    width = float(getattr(page, "width", 0) or 0)
    body_words = [
        word
        for word in words
        if float(word.get("top", 0)) > 35
        and (not height or float(word.get("bottom", 0)) < height - 25)
    ]
    if not body_words:
        body_words = words

    column_count = _detect_column_count(body_words, width)
    columns = _column_boundaries(width, column_count)
    rendered_columns = []
    for left, right in columns:
        column_words = [
            word
            for word in body_words
            if left <= ((float(word["x0"]) + float(word["x1"])) / 2) < right
        ]
        rendered = _render_words_by_lines(column_words)
        if rendered:
            rendered_columns.append(rendered)
    return "\n".join(rendered_columns)


def _detect_column_count(words: list[dict], width: float) -> int:
    if not width:
        return 1
    centers = sorted((float(word["x0"]) + float(word["x1"])) / 2 for word in words)
    if not centers:
        return 1
    thirds = [0, 0, 0]
    for center in centers:
        index = min(2, int(center / (width / 3)))
        thirds[index] += 1
    occupied_thirds = sum(1 for count in thirds if count > max(20, len(centers) * 0.12))
    if occupied_thirds >= 3:
        return 3
    halves = [0, 0]
    for center in centers:
        halves[0 if center < width / 2 else 1] += 1
    if all(count > max(20, len(centers) * 0.2) for count in halves):
        return 2
    return 1


def _column_boundaries(width: float, column_count: int) -> list[tuple[float, float]]:
    if column_count <= 1 or not width:
        return [(0, width or 10_000)]
    return [(index * width / column_count, (index + 1) * width / column_count) for index in range(column_count)]


def _render_words_by_lines(words: list[dict]) -> str:
    if not words:
        return ""
    sorted_words = sorted(words, key=lambda word: (round(float(word["top"]) / 3) * 3, float(word["x0"])))
    lines: list[list[dict]] = []
    for word in sorted_words:
        top = float(word["top"])
        if not lines or abs(top - _line_top(lines[-1])) > 4:
            lines.append([word])
        else:
            lines[-1].append(word)

    rendered_lines = []
    for line_words in lines:
        line = " ".join(word["text"] for word in sorted(line_words, key=lambda word: float(word["x0"])))
        line = _clean_line(line)
        if line and not _is_running_header(line):
            rendered_lines.append(line)
    return "\n".join(rendered_lines)


def _line_top(line_words: list[dict]) -> float:
    return sum(float(word["top"]) for word in line_words) / len(line_words)


def _tables_to_text(tables: list[list[list[str | None]]]) -> str:
    rendered_tables = []
    for table in tables:
        rows = []
        for row in table:
            rows.append(" | ".join((cell or "").strip() for cell in row))
        if rows:
            rendered_tables.append("\n".join(rows))
    return "\n\n".join(rendered_tables)


def build_semantic_pdf_sections(pages: list[dict], *, source_id: str = "") -> list[dict]:
    page_sections = _page_sections(pages)
    if _prefer_page_sections(source_id, page_sections):
        return page_sections
    if _is_cfr_source(source_id):
        cfr_sections = _cfr_sections(pages)
        if cfr_sections:
            return _filter_cfr_sections(source_id, _dedupe_sections_by_ref(cfr_sections))

    sections: list[dict] = []
    current_heading = "Document"
    current_section = "document"
    current_page = None
    current_lines: list[str] = []

    for page in pages:
        page_number = page.get("page")
        for raw_line in str(page.get("text") or "").splitlines():
            line = _clean_line(raw_line)
            if not line or _is_running_header(line):
                continue
            heading = _detect_semantic_heading(line)
            if heading and not _is_toc_leader(line):
                if _meaningful_section(current_lines):
                    sections.append(
                        {
                            "section_label": current_heading,
                            "section": current_section,
                            "text": "\n".join(current_lines).strip(),
                            "page_number": current_page,
                        }
                    )
                current_heading = heading
                current_section = _section_ref(heading)
                current_page = page_number
                current_lines = [line]
            else:
                if current_page is None:
                    current_page = page_number
                current_lines.append(line)

    if _meaningful_section(current_lines):
        sections.append(
            {
                "section_label": current_heading,
                "section": current_section,
                "text": "\n".join(current_lines).strip(),
                "page_number": current_page,
            }
        )

    if _needs_column_order(source_id) and len(sections) >= 5:
        return sections
    return sections if len(sections) >= max(2, len(page_sections) // 3) else page_sections


def _is_cfr_source(source_id: str) -> bool:
    source_key = source_id.lower()
    return source_key.startswith("cfr-") or source_key.startswith("ecfr-")


def _cfr_sections(pages: list[dict]) -> list[dict]:
    lines: list[tuple[int, str]] = []
    for page in pages:
        page_number = page.get("page")
        for raw_line in str(page.get("text") or "").splitlines():
            line = _clean_line(raw_line)
            if line and not _is_running_header(line):
                lines.append((page_number, line))

    body_start = 0
    for index, (_, line) in enumerate(lines):
        if re.match(r"^§\s*\d+[a-z]?\.\d+", line):
            next_lines = " ".join(item[1] for item in lines[index : index + 6])
            if re.search(r"\b(a)\b|\bThe\b|\bYou\b|\bExcept\b|\bFor\b|\bThis\b", next_lines):
                body_start = index
                break

    sections: list[dict] = []
    current_heading = "Document"
    current_section = "document"
    current_page = None
    current_lines: list[str] = []

    for page_number, line in lines[body_start:]:
        heading = line if re.match(r"^§\s*\d+[a-z]?\.\d+", line) else None
        if heading:
            if _meaningful_section(current_lines):
                sections.append(
                    {
                        "section_label": current_heading,
                        "section": current_section,
                        "text": "\n".join(current_lines).strip(),
                        "page_number": current_page,
                    }
                )
            current_heading = heading
            current_section = _section_ref(heading)
            current_page = page_number
            current_lines = [line]
        else:
            if current_page is None:
                current_page = page_number
            current_lines.append(line)

    if _meaningful_section(current_lines):
        sections.append(
            {
                "section_label": current_heading,
                "section": current_section,
                "text": "\n".join(current_lines).strip(),
                "page_number": current_page,
            }
        )
    return sections


def _dedupe_sections_by_ref(sections: list[dict]) -> list[dict]:
    by_ref: dict[str, dict] = {}
    order: list[str] = []
    for section in sections:
        ref = str(section.get("section") or section.get("section_label"))
        current = by_ref.get(ref)
        if current is None:
            by_ref[ref] = section
            order.append(ref)
            continue
        if len(str(section.get("text") or "")) > len(str(current.get("text") or "")):
            by_ref[ref] = section
    return [by_ref[ref] for ref in order]


def _filter_cfr_sections(source_id: str, sections: list[dict]) -> list[dict]:
    source_key = source_id.lower()
    ranges: list[tuple[float, float]] = []
    if "subpart-s" in source_key:
        ranges.append((1.1300, 1.1465))
    elif source_key == "cfr-21-1-subpart-j":
        ranges.append((1.326, 1.368))
    elif source_key == "cfr-21-10-30":
        ranges.append((10.30, 10.30))
    elif source_key == "cfr-21-112-2":
        ranges.append((112.2, 112.2))
    elif source_key == "cfr-21-123-3":
        ranges.append((123.3, 123.3))
    elif source_key == "cfr-21-1240-60":
        ranges.append((1240.60, 1240.60))
    elif source_key == "cfr-21-133-111":
        ranges.append((133.111, 133.111))
    elif source_key == "cfr-21-133-118":
        ranges.append((133.118, 133.118))
    elif source_key == "cfr-21-133-150":
        ranges.append((133.150, 133.150))

    if not ranges:
        return sections

    filtered = []
    for section in sections:
        value = _numeric_section(str(section.get("section") or ""))
        if value is None:
            continue
        if any(start <= value <= end for start, end in ranges):
            filtered.append(section)
    return filtered or sections


def _numeric_section(value: str) -> float | None:
    match = re.search(r"(\d+[a-z]?\.\d+)", value, re.I)
    if not match:
        return None
    cleaned = re.sub(r"[a-z]", "", match.group(1), flags=re.I)
    try:
        return float(cleaned)
    except ValueError:
        return None


def _page_sections(pages: list[dict]) -> list[dict]:
    sections = []
    for page in pages:
        text = str(page.get("text") or "").strip()
        if not text:
            continue
        sections.append(
            {
                "section_label": f"PDF page {page.get('page')}",
                "section": f"page-{page.get('page')}",
                "text": text,
                "page_number": page.get("page"),
            }
        )
    return sections


def _prefer_page_sections(source_id: str, page_sections: list[dict]) -> bool:
    source_key = source_id.lower()
    if "sortable-spreadsheet" in source_key:
        return True
    if "traceability-plan" in source_key:
        return True
    if len(page_sections) <= 3 and not any("cfr" in source_key for _ in [0]):
        return True
    return False


def _detect_semantic_heading(line: str) -> str | None:
    if re.match(r"^§\s*\d+[a-z]?\.\d+\s+(?!\([a-z0-9]\))(?=[A-Z])", line):
        return line
    if re.match(r"^(subpart|part)\s+[a-z0-9-]+[—-]", line, re.I):
        return line
    if re.match(r"^[IVX]{1,7}\.\s+[A-Z]", line):
        return line
    if re.match(r"^[A-Z]\.\s+[A-Z][A-Za-z]", line):
        return line
    if re.match(r"^Question\s+\d+[:.]\s+", line, re.I):
        return line
    if re.match(r"^Table\s+\d+\s*[-—:]", line, re.I):
        return line
    if re.match(r"^Appendix\s+[A-Z0-9]+", line, re.I):
        return line
    if line in {"List of Subjects", "References", "Table of Contents"}:
        return line
    return None


def _section_ref(heading: str) -> str:
    section = re.search(r"§\s*\d+[a-z]?\.\d+", heading, re.I)
    if section:
        return section.group(0).replace(" ", "")
    question = re.search(r"Question\s+\d+", heading, re.I)
    if question:
        return question.group(0)
    marker = re.match(r"^([IVX]{1,7}|[A-Z]{1,3})\.", heading)
    if marker:
        return marker.group(0).rstrip(".")
    table = re.match(r"^(Table\s+\d+)", heading, re.I)
    if table:
        return table.group(1)
    return heading[:80]


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _is_running_header(line: str) -> bool:
    return bool(
        re.search(r"Federal Register/Vol\.", line)
        or re.search(r"\d+\s+Federal Register\s*/", line)
        or re.search(r"\b\d+\s*CFR\s+Ch\.\s+I\b", line)
    )


def _is_toc_leader(line: str) -> bool:
    return bool(
        re.search(r"\.{5,}\s*\d+$", line)
        or re.search(r"…{2,}\s*\d+$", line)
        or re.search(r"[.\u2026]{3,}", line)
    )


def _meaningful_section(lines: list[str]) -> bool:
    text = "\n".join(lines).strip()
    if len(text) < 160:
        return False
    return True
