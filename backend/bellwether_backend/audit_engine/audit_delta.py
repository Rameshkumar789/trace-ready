"""Re-audit delta: assess -> fix -> re-run -> SHOW the improvement.

The corrective-action loop from the advisory calls: run the audit, remediate, run it again,
and hand the customer "what got fixed / what's new / what persists" instead of a second
undifferentiated report. Findings are matched by a stable fingerprint (type + cte + the
stable subject of the message: lot, product, or affected fields), not by finding_id, which
renumbers between runs.
"""

from __future__ import annotations

import re
from typing import Any


def _fingerprint(finding: dict[str, Any]) -> str:
    finding_type = finding.get("finding_type", "")
    cte = finding.get("cte") or ""
    message = finding.get("message", "")
    # Anchor on the stable subject inside the message: a lot code or product id if present.
    subject = ""
    lot_match = re.search(r"\b(?:lot|Lot)\s+([A-Z0-9][A-Z0-9\-]{3,})", message)
    if lot_match:
        subject = lot_match.group(1)
    else:
        product_match = re.search(r"\bProduct\s+(\S+)", message)
        if product_match:
            subject = product_match.group(1)
    affected = ",".join(sorted(finding.get("affected_fields") or []))
    return f"{finding_type}|{cte}|{subject}|{affected}"


def diff_audit_findings(
    previous_findings: list[dict[str, Any]],
    current_findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Both inputs are lists of AuditFinding dicts (model_dump / the persisted artifact)."""
    previous_by_fp: dict[str, list[dict[str, Any]]] = {}
    for finding in previous_findings:
        previous_by_fp.setdefault(_fingerprint(finding), []).append(finding)
    current_by_fp: dict[str, list[dict[str, Any]]] = {}
    for finding in current_findings:
        current_by_fp.setdefault(_fingerprint(finding), []).append(finding)

    fixed = [
        {"fingerprint": fp, "finding_type": items[0].get("finding_type"), "message": items[0].get("message", "")[:200]}
        for fp, items in sorted(previous_by_fp.items())
        if fp not in current_by_fp
    ]
    new = [
        {"fingerprint": fp, "finding_type": items[0].get("finding_type"), "severity": items[0].get("severity"), "message": items[0].get("message", "")[:200]}
        for fp, items in sorted(current_by_fp.items())
        if fp not in previous_by_fp
    ]
    persisting = [
        {"fingerprint": fp, "finding_type": items[0].get("finding_type"), "severity": items[0].get("severity"), "message": items[0].get("message", "")[:200]}
        for fp, items in sorted(current_by_fp.items())
        if fp in previous_by_fp
    ]

    def _sev(findings: list[dict[str, Any]], severity: str) -> int:
        return sum(1 for finding in findings if finding.get("severity") == severity)

    return {
        "previous_total": len(previous_findings),
        "current_total": len(current_findings),
        "fixed_count": len(fixed),
        "new_count": len(new),
        "persisting_count": len(persisting),
        "high_severity_delta": _sev(current_findings, "high") - _sev(previous_findings, "high"),
        "fixed": fixed[:50],
        "new": new[:50],
        "persisting": persisting[:50],
        "headline": (
            f"{len(fixed)} finding(s) resolved since the previous audit, "
            f"{len(new)} new, {len(persisting)} still open."
        ),
    }
