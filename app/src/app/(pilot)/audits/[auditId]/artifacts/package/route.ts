import { NextResponse } from "next/server";
import { runDemoAudit } from "@/lib/audit/demo-audit";
import { getPilotSession } from "@/lib/auth/session";
import { canAccessPath } from "@/lib/auth/session-cookie";
import { loadOperatorAuditArtifact } from "@/lib/audit/operator-audit-db";
import { buildAuditExportPackage } from "@/lib/report/export-package";
import type { StoredAudit } from "@/lib/audit/stored-audit";

export async function GET(_request: Request, { params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  const session = await getPilotSession();
  if (!session || !canAccessPath(session, `/audits/${auditId}/artifacts/package`)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (auditId === "demo") {
    return jsonDownload(buildAuditExportPackage(demoAsStored()), `traceready-audit-package-${auditId}.json`);
  }
  const artifact = await loadOperatorAuditArtifact(auditId, ["exportPackage"], session);
  if (!artifact) {
    return NextResponse.json({ error: "Export package artifact is not available for this audit yet." }, { status: 404 });
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

function demoAsStored(): StoredAudit {
  const audit = runDemoAudit();
  return {
    auditId: "demo",
    createdAt: "2026-06-14T00:00:00.000Z",
    fileName: "demo",
    parseErrors: [],
    dataset: {
      businessProfiles: [],
      exemptionClaims: [],
      products: [],
      productScopeDecisions: [],
      traceabilityPlans: [],
      events: [],
      lineItems: [],
      kdeValues: [],
      lineage: [],
      sourceDocuments: []
    },
    findings: audit.findings,
    readinessGate: audit.readinessGate,
    coverage: audit.coverage,
    mode: "draft"
  };
}
