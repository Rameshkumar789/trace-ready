import type React from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { notFound, redirect } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadOperatorAuditArtifact, loadOperatorStoredAudit } from "@/lib/audit/operator-audit-db";
import { generateAuditReport } from "@/lib/report/audit-report";

export default async function ReportPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}/report`)) {
    redirect(`/login/operator?auth=required&next=${encodeURIComponent(`/audits/${auditId}/report`)}`);
  }
  const report =
    auditId === "demo"
      ? generateAuditReport(runDemoAudit())
      : await loadReportMarkdown(auditId, session);
  if (!report) notFound();

  return (
    <AppShell>
      <div className="toolbar">
        <div>
          {auditId !== "demo" ? (
            <Link className="audit-breadcrumb" href={`/audits/${auditId}`}>
              <ChevronLeft size={16} />
              Back to audit
            </Link>
          ) : null}
          <h1>FSMA 204 Readiness Report</h1>
          <p className="muted">Readiness review, not legal certification.</p>
        </div>
        <a className="button secondary" href={`/audits/${auditId}/artifacts/package`}>
          Download report
        </a>
        <a className="button secondary" href={`/audits/${auditId}/artifacts/workbook`}>
          Download XLSX
        </a>
      </div>
      <article className="panel report-markdown">{renderMarkdown(report.markdown)}</article>
    </AppShell>
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
