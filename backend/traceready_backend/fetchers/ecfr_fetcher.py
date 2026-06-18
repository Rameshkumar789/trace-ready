from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SourceSnapshot:
    url: str
    body: bytes
    text: str
    content_type: str
    retrieved_at: str


def fetch_url(url: str) -> SourceSnapshot:
    request = Request(url, headers={"User-Agent": "TraceReady regulatory ingestion"})
    with urlopen(request, timeout=30) as response:
        body = response.read()
        content_type = response.headers.get("content-type", "text/html")
    return SourceSnapshot(
        url=url,
        body=body,
        text=body.decode("utf-8", errors="replace"),
        content_type=content_type,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
