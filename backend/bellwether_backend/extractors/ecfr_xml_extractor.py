from __future__ import annotations

import re
import xml.etree.ElementTree as ET


def extract_ecfr_sections(xml_text: str, *, min_section: float | None = None, max_section: float | None = None) -> list[dict]:
    root = ET.fromstring(xml_text)
    sections: list[dict] = []
    for element in root.iter():
        if element.tag.upper() != "DIV8" or element.attrib.get("TYPE") != "SECTION":
            continue
        section = element.attrib.get("N", "").strip()
        section_number = _section_number(section)
        if section_number is None:
            continue
        if min_section is not None and section_number < min_section:
            continue
        if max_section is not None and section_number > max_section:
            continue

        heading = _heading(element) or f"21 CFR {section}"
        paragraphs = [_clean_text(" ".join(node.itertext())) for node in element if node.tag.upper() != "HEAD"]
        text = " ".join(paragraph for paragraph in paragraphs if paragraph)
        if not text:
            continue
        sections.append(
            {
                "section_label": heading,
                "section": f"21 CFR {section}",
                "text": text,
            }
        )
    return sections


def _heading(element: ET.Element) -> str | None:
    for child in element:
        if child.tag.upper() == "HEAD":
            return _clean_text(" ".join(child.itertext()))
    return None


def _section_number(value: str) -> float | None:
    match = re.match(r"^1\.(\d+)$", value)
    if not match:
        return None
    return float(value)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
