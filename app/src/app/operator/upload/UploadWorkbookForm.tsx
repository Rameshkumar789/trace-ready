"use client";

import { useState } from "react";
import Link from "next/link";
import { Download, FileSpreadsheet, UploadCloud } from "lucide-react";

export function UploadWorkbookForm({ action }: { action: (formData: FormData) => void | Promise<void> }) {
  const [fileName, setFileName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  return (
    <form
      action={action}
      className="upload-records-form"
      onSubmit={() => setIsSubmitting(true)}
    >
      <label className={`records-dropzone ${fileName ? "has-file" : ""}`}>
        <input
          accept=".xlsx,.xlsm,.csv,.edi,.x12,.asn,.xml"
          name="workbook"
          onChange={(event) => setFileName(event.currentTarget.files?.[0]?.name ?? "")}
          required
          type="file"
        />
        <span className="dropzone-icon" aria-hidden="true">
          {fileName ? <FileSpreadsheet /> : <UploadCloud />}
        </span>
        <strong>{fileName || "Choose your workbook"}</strong>
        <span>{fileName ? "Ready to upload" : "Click to browse for a Bellwether workbook"}</span>
        <small>Supported formats</small>
        <span className="format-chips" aria-label="Supported upload formats">
          <b>XLSX</b>
          <b>XLSM</b>
        </span>
      </label>

      <div className="upload-records-actions">
        <button className="button large" disabled={!fileName || isSubmitting} type="submit">
          <UploadCloud aria-hidden="true" />
          {isSubmitting ? "Uploading..." : "Upload records"}
        </button>
        <Link className="template-inline-link" href="/operator/upload/template">
          <Download aria-hidden="true" />
          Download template
        </Link>
      </div>
    </form>
  );
}
