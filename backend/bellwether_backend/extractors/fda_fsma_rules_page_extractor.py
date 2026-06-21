from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin


FDA_BASE_URL = "https://www.fda.gov"


class FsmaRulesEntryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[dict] = []
        self._heading = ""
        self._in_row = False
        self._in_cell = False
        self._cell_index = -1
        self._cells: list[list[str]] = []
        self._links: list[dict] = []
        self._active_link: str | None = None
        self._active_link_text: list[str] = []
        self._tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        self._tag_stack.append(tag)
        attr_map = dict(attrs)
        if tag == "tr":
            self._in_row = True
            self._cells = []
            self._links = []
            self._cell_index = -1
        elif tag == "td" and self._in_row:
            self._in_cell = True
            self._cell_index += 1
            self._cells.append([])
        elif tag == "a" and self._in_row and attr_map.get("href"):
            self._active_link = urljoin(FDA_BASE_URL, attr_map["href"])
            self._active_link_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "h2":
            heading = self._consume_heading()
            if heading in {"Rules", "Guidance for Industry & Others"}:
                self._heading = heading
        elif tag == "a" and self._active_link:
            text = _clean(" ".join(self._active_link_text))
            if text:
                self._links.append({"text": text, "url": self._active_link})
            self._active_link = None
            self._active_link_text = []
        elif tag == "td":
            self._in_cell = False
        elif tag == "tr":
            self._finalize_row()
            self._in_row = False
            self._in_cell = False
            self._cell_index = -1
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        text = _clean(data)
        if not text:
            return
        current_tag = self._tag_stack[-1] if self._tag_stack else ""
        if current_tag == "h2":
            self._active_link_text.append(text)
            return
        if self._active_link:
            self._active_link_text.append(text)
        if self._in_cell and self._cell_index >= 0:
            self._cells[self._cell_index].append(text)

    def _consume_heading(self) -> str:
        text = _clean(" ".join(self._active_link_text))
        self._active_link_text = []
        return text

    def _finalize_row(self) -> None:
        if self._heading not in {"Rules", "Guidance for Industry & Others"}:
            return
        if len(self._cells) < 2:
            return
        title_cell = _clean(" ".join(self._cells[0]))
        date_cell = _clean(" ".join(self._cells[1]))
        if not title_cell or title_cell.lower() == "title":
            return

        docket = _extract_docket(title_cell)
        document_type = _extract_document_type(title_cell)
        title = _extract_title(title_cell, document_type, docket)
        primary_link = _first_non_docket_link(self._links)
        docket_link = _first_docket_link(self._links)
        self.entries.append(
            {
                "category": self._heading,
                "document_type": document_type,
                "title": title,
                "docket": docket,
                "issued_date": date_cell,
                "primary_url": primary_link,
                "docket_url": docket_link,
                "raw_text": title_cell,
            }
        )


def extract_fsma_rules_guidance_entries(html: str) -> list[dict]:
    parser = FsmaRulesEntryParser()
    parser.feed(html)
    return parser.entries


def extract_fsma_rules_guidance_sections(html: str) -> list[dict]:
    sections = []
    for index, entry in enumerate(extract_fsma_rules_guidance_entries(html), start=1):
        title = entry["title"]
        docket = entry.get("docket") or "no docket"
        date = entry.get("issued_date") or "no date"
        category = entry["category"]
        doc_type = entry["document_type"]
        sections.append(
            {
                "section_label": f"{category}: {doc_type}: {title}",
                "section": docket,
                "text": (
                    f"{category} entry. Document type: {doc_type}. Title: {title}. "
                    f"Docket: {docket}. Issued date: {date}. "
                    f"Primary URL: {entry.get('primary_url') or 'not listed'}. "
                    f"Docket URL: {entry.get('docket_url') or 'not listed'}."
                ),
                "metadata": entry,
            }
        )
    return sections


def _extract_document_type(value: str) -> str:
    match = re.match(r"^([^:]+):", value)
    return _clean(match.group(1)) if match else "Document"


def _extract_title(value: str, document_type: str, docket: str | None) -> str:
    text = re.sub(rf"^{re.escape(document_type)}:\s*", "", value)
    text = re.sub(r"Docket Number:.*$", "", text).strip()
    if docket:
        text = text.replace(docket, "").strip()
    return _clean(text)


def _extract_docket(value: str) -> str | None:
    match = re.search(r"FDA-\d{4}-[A-Z]-\d{4}", value)
    return match.group(0) if match else None


def _first_non_docket_link(links: list[dict]) -> str | None:
    for link in links:
        text = link["text"]
        if not _extract_docket(text):
            return link["url"]
    return links[0]["url"] if links else None


def _first_docket_link(links: list[dict]) -> str | None:
    for link in links:
        if _extract_docket(link["text"]) or "regulations.gov" in link["url"]:
            return link["url"]
    return None


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()
