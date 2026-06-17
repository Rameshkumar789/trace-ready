import type { CTEType } from "./types";

export const cteTypes: CTEType[] = [
  "harvest",
  "cooling",
  "initial_packing",
  "first_land_based_receiving",
  "shipping",
  "receiving",
  "transformation"
];

export function isCteType(value: string): value is CTEType {
  return cteTypes.includes(value as CTEType);
}
