import { NextResponse } from "next/server";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/roles";
import { loadOperatorAuditArtifact } from "@/lib/audit/operator-audit-db";
import { findingsToRows } from "@/lib/report/export-audit-xlsx";

export async function GET(_request: Request, { params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/operator/audits/${auditId}/artifacts/findings`)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (auditId === "demo") {
    return jsonDownload(findingsToRows(runDemoAudit().findings), `bellwether-findings-${auditId}.json`);
  }
  const artifact = await loadOperatorAuditArtifact(auditId, ["auditFindings"], session);
  if (!artifact) {
    return NextResponse.json({ error: "Findings artifact is not available for this audit yet." }, { status: 404 });
  }
  return artifactDownload(artifact.body, artifact.fileName, artifact.contentType);
}

function jsonDownload(body: unknown, fileName: string) {
  return new NextResponse(JSON.stringify(body, null, 2), {
    headers: {
      "content-type": "application/json",
      "content-disposition": `attachment; filename="${fileName}"`
    }
  });
}

function artifactDownload(body: Uint8Array, fileName: string, contentType: string) {
  return new NextResponse(toArrayBuffer(body), {
    headers: {
      "content-type": contentType,
      "content-disposition": `attachment; filename="${fileName}"`
    }
  });
}

function toArrayBuffer(body: Uint8Array) {
  const buffer = new ArrayBuffer(body.byteLength);
  new Uint8Array(buffer).set(body);
  return buffer;
}
