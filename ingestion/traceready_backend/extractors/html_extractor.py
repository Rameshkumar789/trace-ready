from __future__ import annotations

import re
from html.parser import HTMLParser


class _SectionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._tag_stack: list[str] = []
        self._current_heading = "Document"
        self._current_text: list[str] = []
        self.sections: list[dict] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self._tag_stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"h1", "h2", "h3"}:
            self._flush()
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        tag = self._tag_stack[-1] if self._tag_stack else ""
        if tag in {"h1", "h2", "h3"}:
            self._flush()
            self._current_heading = text
        elif tag in {"p", "li", "td", "th", "div", "span"}:
            self._current_text.append(text)

    def _flush(self) -> None:
        text = " ".join(self._current_text).strip()
        if text:
            self.sections.append(
                {
                    "section_label": self._current_heading,
                    "section": _find_section(self._current_heading, text),
                    "text": text,
                }
            )
        self._current_text = []


def extract_html_sections(html: str) -> list[dict]:
    parser = _SectionParser()
    parser.feed(html)
    parser._flush()
    return parser.sections or [{"section_label": "Document", "section": "document", "text": re.sub(r"<[^>]+>", " ", html)}]


def _find_section(heading: str, text: str) -> str:
    match = re.search(r"(?:21\s*CFR\s*)?1\.\d{4}", f"{heading} {text}", re.I)
    return match.group(0) if match else heading
