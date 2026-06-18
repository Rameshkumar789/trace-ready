import Link from "next/link";
import { ArrowRight, CheckCircle2, Download, FileSpreadsheet, Info, LockKeyhole, Target, TriangleAlert } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { requiredWorkbookSheets } from "@/lib/import/workbook-schema";
import { uploadWorkbookAction } from "./actions";
import { UploadWorkbookForm } from "./UploadWorkbookForm";

// The upload action runs parse + rule execution synchronously (no cron/queue worker), so the
// server function needs room to finish the full audit before returning. Raise the Vercel
// function timeout for this route accordingly (Hobby allows up to 60s).
export const maxDuration = 60;

const afterUploadSteps = [
  {
    title: "Scope check",
    detail: "TraceReady checks covered food, entity role, and exemptions.",
    tone: "blue",
    icon: Target
  },
  {
    title: "KDE/TLC gap report",
    detail: "See what is missing, incomplete, or inconsistent.",
    tone: "amber",
    icon: TriangleAlert
  },
  {
    title: "Sortable readiness export",
    detail: "Download an FDA-style package with citations and evidence links.",
    tone: "green",
    icon: FileSpreadsheet
  }
] as const;

export default async function UploadPage({ searchParams }: { searchParams?: Promise<{ error?: string }> }) {
  const resolvedSearchParams = await searchParams;

  return (
    <AppShell>
      <section className="upload-records-page">
        <div className="upload-records-card">
          <div className="upload-records-main">
            <div className="upload-records-header">
              <div>
                <h1>Start a readiness audit</h1>
                <p>Upload an Excel workbook or mapped traceability export.</p>
              </div>
              <Link className="template-link" href="/upload/template">
                <Download aria-hidden="true" />
                Download template
              </Link>
            </div>

            {resolvedSearchParams?.error ? <p className="upload-error">{resolvedSearchParams.error}</p> : null}

            <UploadWorkbookForm action={uploadWorkbookAction} />

            <div className="upload-state-row">
              <div className="file-tile" aria-hidden="true">
                <FileSpreadsheet />
              </div>
              <div>
                <strong>Ready for your first workbook</strong>
                <span>{requiredWorkbookSheets.length} required sheets checked during upload</span>
              </div>
              <em>Waiting</em>
              <ArrowRight aria-hidden="true" />
            </div>
          </div>

          <aside className="after-upload-panel" aria-label="What happens after upload">
            <h2>After upload</h2>
            <div className="after-upload-list">
              {afterUploadSteps.map(({ title, detail, tone, icon: Icon }) => (
                <div className="after-upload-item" key={title}>
                  <span className={`after-upload-icon ${tone}`}>
                    <Icon aria-hidden="true" />
                  </span>
                  <div>
                    <strong>{title}</strong>
                    <p>{detail}</p>
                  </div>
                  <ArrowRight aria-hidden="true" />
                </div>
              ))}
            </div>
            <div className="secure-note">
              <LockKeyhole aria-hidden="true" />
              <div>
                <strong>Secure and audit-ready</strong>
                <p>Files are stored in controlled audit folders and processed through the readiness engine.</p>
              </div>
            </div>
          </aside>
        </div>

        <div className="upload-tip-bar">
          <Info aria-hidden="true" />
          <div>
            <strong>Tip</strong>
            <span>Use the template to format event, lot, receiving, shipping, and transformation records correctly.</span>
          </div>
          <Link href="/upload/template">
            <Download aria-hidden="true" />
            Download template
          </Link>
        </div>
      </section>
    </AppShell>
  );
}
