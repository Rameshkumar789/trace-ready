import type React from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { notFound, redirect } from "next/navigation";
import { BellwetherShell } from "@/components/bellwether/BellwetherShell";
import { MONO, SERIF } from "@/components/bellwether/brand";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/roles";
import { loadOperatorAuditArtifact, loadOperatorStoredAudit } from "@/lib/audit/operator-audit-db";
import { generateAuditReport } from "@/lib/report/audit-report";

export default async function ReportPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/operator/audits/${auditId}/report`)) {
    redirect(`/login/operator?auth=required&next=${encodeURIComponent(`/operator/audits/${auditId}/report`)}`);
  }
  const report =
    auditId === "demo"
      ? generateAuditReport(runDemoAudit())
      : await loadReportMarkdown(auditId, session);
  if (!report) notFound();

  const downloadBtn = {
    display: "inline-flex",
    alignItems: "center",
    height: 40,
    padding: "0 16px",
    borderRadius: 8,
    border: "1px solid #C9C1AF",
    background: "#FBFAF5",
    color: "#1A1813",
    fontSize: 13.5,
    fontWeight: 600,
    textDecoration: "none"
  } as const;

  return (
    <BellwetherShell active="audits" topbarLeft="AUDIT · READINESS REPORT">
      <div style={{ padding: 28 }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            {auditId !== "demo" ? (
              <Link
                href={`/operator/audits/${auditId}`}
                style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 13, color: "#6E6757", textDecoration: "none" }}
              >
                <ChevronLeft size={15} />
                Back to audit
              </Link>
            ) : null}
            <h1 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 28, fontWeight: 500, letterSpacing: "-.015em" }}>FSMA 204 Readiness Report</h1>
            <p style={{ margin: "4px 0 0", fontFamily: MONO, fontSize: 11, letterSpacing: ".04em", color: "#9A9181" }}>READINESS REVIEW, NOT LEGAL CERTIFICATION.</p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <a style={downloadBtn} href={`/operator/audits/${auditId}/artifacts/package`}>Download report</a>
            <a style={downloadBtn} href={`/operator/audits/${auditId}/artifacts/workbook`}>Download XLSX</a>
          </div>
        </div>
        <article className="report-markdown" style={{ marginTop: 20, background: "#FBFAF5", border: "1px solid #DDD6C7", borderRadius: 12, padding: "28px 32px" }}>
          {renderMarkdown(report.markdown)}
        </article>
      </div>
    </BellwetherShell>
  );
}

async function loadReportMarkdown(auditId: string, session: NonNullable<Awaited<ReturnType<typeof getPilotSession>>>) {
  const artifact = await loadOperatorAuditArtifact(auditId, ["reportMarkdown", "auditReport", "report"], session).catch(() => undefined);
  if (artifact) {
    return { markdown: new TextDecoder().decode(artifact.body) };
  }
  const audit = await loadOperatorStoredAudit(auditId, session);
  return audit ? generateAuditReport(audit) : undefined;
}

// Lightweight, dependency-free Markdown rendering for the report sections
// (headings, lists, pipe tables, horizontal rules, bold, inline code).
function renderMarkdown(markdown: string): React.ReactNode {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const trimmed = lines[i].trim();
    if (!trimmed) {
      i++;
      continue;
    }

    const heading = /^(#{1,4})\s+(.*)$/.exec(trimmed);
    if (heading) {
      blocks.push(
        <Heading key={`b-${key++}`} level={heading[1].length}>
          {renderInline(heading[2], `h-${key}`)}
        </Heading>
      );
      i++;
      continue;
    }

    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push(<hr key={`b-${key++}`} />);
      i++;
      continue;
    }

    const next = i + 1 < lines.length ? lines[i + 1].trim() : "";
    if (trimmed.includes("|") && next.includes("-") && /^[\s|:-]+$/.test(next)) {
      const header = splitRow(trimmed);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().includes("|")) {
        rows.push(splitRow(lines[i].trim()));
        i++;
      }
      const tableKey = key++;
      blocks.push(
        <table key={`b-${tableKey}`}>
          <thead>
            <tr>{header.map((cell, ci) => <th key={ci}>{renderInline(cell, `th-${tableKey}-${ci}`)}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri}>{row.map((cell, ci) => <td key={ci}>{renderInline(cell, `td-${tableKey}-${ri}-${ci}`)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      );
      continue;
    }

    if (/^[-*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
      const ordered = /^\d+\.\s+/.test(trimmed);
      const items: React.ReactNode[] = [];
      const listKey = key++;
      let li = 0;
      while (i < lines.length && (/^[-*]\s+/.test(lines[i].trim()) || /^\d+\.\s+/.test(lines[i].trim()))) {
        const itemText = lines[i].trim().replace(/^([-*]|\d+\.)\s+/, "");
        items.push(<li key={li}>{renderInline(itemText, `li-${listKey}-${li}`)}</li>);
        li++;
        i++;
      }
      blocks.push(ordered ? <ol key={`b-${listKey}`}>{items}</ol> : <ul key={`b-${listKey}`}>{items}</ul>);
      continue;
    }

    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,4})\s+/.test(lines[i].trim()) &&
      !/^[-*]\s+/.test(lines[i].trim()) &&
      !/^\d+\.\s+/.test(lines[i].trim()) &&
      !/^(-{3,}|\*{3,}|_{3,})$/.test(lines[i].trim())
    ) {
      para.push(lines[i].trim());
      i++;
    }
    blocks.push(<p key={`b-${key++}`}>{renderInline(para.join(" "), `p-${key}`)}</p>);
  }

  return blocks;
}

function Heading({ level, children }: { level: number; children: React.ReactNode }) {
  if (level <= 1) return <h2>{children}</h2>;
  if (level === 2) return <h3>{children}</h3>;
  if (level === 3) return <h4>{children}</h4>;
  return <h5>{children}</h5>;
}

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  parts.forEach((part, index) => {
    if (!part) return;
    if (part.startsWith("**") && part.endsWith("**")) {
      nodes.push(<strong key={`${keyPrefix}-b-${index}`}>{part.slice(2, -2)}</strong>);
    } else if (part.startsWith("`") && part.endsWith("`")) {
      nodes.push(<code key={`${keyPrefix}-c-${index}`}>{part.slice(1, -1)}</code>);
    } else {
      nodes.push(part);
    }
  });
  return nodes;
}

function splitRow(line: string): string[] {
  return line.replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
}
