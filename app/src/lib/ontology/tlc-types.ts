import type { TraceabilityLotCode } from "./types";

export function hasTlc(value: string | undefined): value is string {
  return Boolean(value?.trim());
}

export function createTraceabilityLotCode(value: string, sourceLocationId?: string, sourceReference?: string): TraceabilityLotCode {
  return {
    value,
    sourceLocationId,
    sourceReference
  };
}
