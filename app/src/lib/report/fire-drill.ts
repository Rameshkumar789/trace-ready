import type { NormalizedAuditDataset } from "@/lib/ontology/types";

/**
 * P5 — 24-hr traceback fire-drill (frontend mirror of the Python run_traceback_fire_drill).
 * Pick a lot and ask: could we assemble a complete one-up / one-down linked record? Scored
 * over {found, one-up source, one-down destination}; passes only if all three hold. Runs over
 * the already-loaded dataset, so no backend round-trip is needed.
 */

export interface FireDrillResult {
  targetLot: string;
  eventCount: number;
  eventIds: string[];
  oneUpLinked: boolean;
  oneDownLinked: boolean;
  completenessScore: number;
  passed: boolean;
  missingLinks: string[];
}

const RECEIVE_CTES = new Set(["receiving", "first_land_based_receiving", "initial_packing", "harvesting"]);

export function runTracebackFireDrill(dataset: NormalizedAuditDataset, targetLot: string): FireDrillResult {
  const needle = (targetLot ?? "").trim().toLowerCase();
  if (!needle) {
    return { targetLot, eventCount: 0, eventIds: [], oneUpLinked: false, oneDownLinked: false, completenessScore: 0, passed: false, missingLinks: ["no lot code entered"] };
  }

  // Event ids whose line items reference this lot.
  const eventIdsForLot = new Set<string>();
  for (const line of dataset.lineItems) {
    const lot = (line.lotOrTlc ?? "").trim().toLowerCase();
    if (lot && lot === needle) eventIdsForLot.add(line.eventId);
  }

  const eventById = new Map(dataset.events.map((event) => [event.eventId, event]));
  const matchingEvents = [...eventIdsForLot].map((id) => eventById.get(id)).filter(Boolean) as typeof dataset.events;

  let oneUp = false;
  let oneDown = false;
  for (const event of matchingEvents) {
    if (RECEIVE_CTES.has(event.eventType)) oneUp = true;
    if (event.eventType === "shipping") oneDown = true;
  }
  // Transformation source link: lineage row whose target is this lot and which has a source.
  for (const link of dataset.lineage) {
    const target = (link.targetLotOrTlc ?? "").trim().toLowerCase();
    const source = (link.sourceLotOrTlc ?? "").trim().toLowerCase();
    if (target === needle && source) oneUp = true;
  }

  const found = matchingEvents.length > 0 || dataset.lineage.some((l) => (l.targetLotOrTlc ?? "").trim().toLowerCase() === needle);
  const components = [found, oneUp, oneDown];
  const score = Math.round((components.filter(Boolean).length / components.length) * 1000) / 1000;
  const missing: string[] = [];
  if (!found) missing.push("no record references this lot");
  if (!oneUp) missing.push("no one-up source (where the lot came from)");
  if (!oneDown) missing.push("no one-down destination (where the lot went)");

  return {
    targetLot,
    eventCount: matchingEvents.length,
    eventIds: matchingEvents.map((e) => e.eventId).sort(),
    oneUpLinked: oneUp,
    oneDownLinked: oneDown,
    completenessScore: score,
    passed: found && oneUp && oneDown,
    missingLinks: missing
  };
}
