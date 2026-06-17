import type { Prisma } from "@prisma/client";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import type { Finding } from "@/lib/findings/finding";
import type { EvidenceRef, NormalizedAuditDataset } from "@/lib/ontology/types";
import { getPrismaClient, type TraceReadyPrismaClient } from "@/lib/db/prisma";
import type { AuditRepository } from "./audit-repository";

export class PrismaStoredAuditRepository implements AuditRepository {
  constructor(private readonly client: Pick<TraceReadyPrismaClient, "auditProject" | "gapFinding"> = getPrismaClient()) {}

  async save(audit: StoredAudit): Promise<void> {
    await this.client.auditProject.upsert({
      where: { id: audit.auditId },
      update: {
        fileName: audit.fileName,
        mode: audit.mode,
        status: audit.readinessGate.passed ? "succeeded" : "needs_review",
        datasetJson: json(audit.dataset),
        parseErrors: json(audit.parseErrors),
        metadataJson: json({
          legacyRepositoryAdapter: "prisma",
          readinessGate: audit.readinessGate,
          coverage: audit.coverage,
          governance: audit.governance
        })
      },
      create: {
        id: audit.auditId,
        fileName: audit.fileName,
        mode: audit.mode,
        status: audit.readinessGate.passed ? "succeeded" : "needs_review",
        datasetJson: json(audit.dataset),
        parseErrors: json(audit.parseErrors),
        metadataJson: json({
          legacyRepositoryAdapter: "prisma",
          readinessGate: audit.readinessGate,
          coverage: audit.coverage,
          governance: audit.governance
        })
      }
    });
    for (const finding of audit.findings) {
      await this.client.gapFinding.upsert({
        where: { id: finding.findingId },
        update: findingData(audit.auditId, finding),
        create: {
          id: finding.findingId,
          ...findingData(audit.auditId, finding)
        }
      });
    }
  }

  async load(auditId: string): Promise<StoredAudit | undefined> {
    const project = await this.client.auditProject.findUnique({
      where: { id: auditId },
      include: {
        findings: {
          orderBy: { createdAt: "asc" }
        }
      }
    });
    if (!project) return undefined;
    const metadata = asRecord(project.metadataJson);
    const findings = project.findings.map((finding) => ({
      findingId: finding.id,
      title: finding.title,
      status: finding.status as Finding["status"],
      severity: finding.severity as Finding["severity"],
      findingType: finding.findingType,
      eventId: finding.eventId ?? undefined,
      eventLineId: finding.eventLineId ?? undefined,
      fieldOrKde: finding.fieldOrKde ?? undefined,
      observedValue: finding.observedValue ?? undefined,
      expectedOrRequired: finding.expectedOrRequired ?? undefined,
      recommendation: finding.recommendation,
      ruleCardId: finding.ruleCardId ?? finding.approvedRecordId ?? finding.approvedObligationId ?? finding.checkCode ?? "approved-rule",
      ruleCardVersion: finding.ruleCardVersion ?? finding.rulePackageVersion ?? 1,
      sourceChunkId: finding.sourceChunkId ?? "approved-source",
      kdeRequirementId: finding.kdeRequirementId ?? undefined,
      evidenceRefs: evidenceRefs(finding.evidenceRefsJson),
      reviewState: reviewState(finding.reviewState)
    }));
    const readinessGate = asReadinessGate(metadata.readinessGate, findings);
    return {
      auditId: project.id,
      createdAt: project.createdAt.toISOString(),
      fileName: project.fileName,
      parseErrors: Array.isArray(project.parseErrors) ? project.parseErrors as unknown as StoredAudit["parseErrors"] : [],
      dataset: asDataset(project.datasetJson),
      findings,
      readinessGate,
      coverage: Array.isArray(metadata.coverage) ? metadata.coverage as StoredAudit["coverage"] : [],
      mode: project.mode === "customer_facing" ? "customer_facing" : "draft",
      governance: Object.keys(asRecord(metadata.governance)).length ? asRecord(metadata.governance) as unknown as StoredAudit["governance"] : undefined
    };
  }
}

function findingData(auditProjectId: string, finding: Finding) {
  return {
    auditProjectId,
    title: finding.title,
    status: finding.status,
    severity: finding.severity,
    findingType: finding.findingType,
    eventId: finding.eventId,
    eventLineId: finding.eventLineId,
    fieldOrKde: finding.fieldOrKde,
    observedValue: finding.observedValue,
    expectedOrRequired: finding.expectedOrRequired,
    recommendation: finding.recommendation,
    ruleCardId: finding.ruleCardId,
    ruleCardVersion: finding.ruleCardVersion,
    sourceChunkId: finding.sourceChunkId,
    kdeRequirementId: finding.kdeRequirementId,
    evidenceRefsJson: json(finding.evidenceRefs),
    reviewState: finding.reviewState
  };
}

function asReadinessGate(value: unknown, findings: Finding[]): StoredAudit["readinessGate"] {
  const record = asRecord(value);
  if (typeof record.passed === "boolean" && Array.isArray(record.blockers)) {
    return { passed: record.passed, blockers: record.blockers.filter((item): item is string => typeof item === "string") };
  }
  const blockers = findings.filter((finding) => !["pass", "not_applicable"].includes(finding.status)).map((finding) => finding.findingId);
  return { passed: blockers.length === 0, blockers };
}

function asDataset(value: unknown): NormalizedAuditDataset {
  const record = asRecord(value);
  return {
    businessProfiles: asArray(record.businessProfiles),
    exemptionClaims: asArray(record.exemptionClaims),
    products: asArray(record.products),
    productScopeDecisions: asArray(record.productScopeDecisions),
    traceabilityPlans: asArray(record.traceabilityPlans),
    events: asArray(record.events),
    lineItems: asArray(record.lineItems),
    kdeValues: asArray(record.kdeValues),
    lineage: asArray(record.lineage),
    sourceDocuments: asArray(record.sourceDocuments)
  } as NormalizedAuditDataset;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function evidenceRefs(value: unknown): EvidenceRef[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is EvidenceRef => Boolean(item) && typeof item === "object" && !Array.isArray(item));
}

function reviewState(value: string): Finding["reviewState"] {
  if (["pending", "approved", "edited", "dismissed", "needs_more_evidence"].includes(value)) {
    return value as Finding["reviewState"];
  }
  return "pending";
}

function json(value: unknown): Prisma.InputJsonValue {
  return value as Prisma.InputJsonValue;
}
