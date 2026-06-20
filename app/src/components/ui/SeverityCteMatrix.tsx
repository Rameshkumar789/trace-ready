import type { Finding } from "@/lib/findings/finding";
import type { FindingSeverity } from "@/lib/ontology/types";
import { Card } from "./Card";
import { CTE_SHORT } from "./finding-format";

const SEVERITY_ROWS: { key: FindingSeverity; label: string; tone: "risk" | "review" }[] = [
  { key: "critical", label: "Critical", tone: "risk" },
  { key: "high", label: "High", tone: "risk" },
  { key: "medium", label: "Medium", tone: "review" },
  { key: "low", label: "Low", tone: "review" },
];

/** A severity × CTE heat grid summarising where findings concentrate. */
export function SeverityCteMatrix({ findings }: { findings: Finding[] }) {
  // Columns: CTE buckets actually present in the findings (+ "Other").
  const colKeys = new Set<string>();
  let hasOther = false;
  for (const f of findings) {
    const key = f.fieldOrKde ?? "";
    if (CTE_SHORT[key]) colKeys.add(key);
    else hasOther = true;
  }
  const columns = [...colKeys];
  if (hasOther) columns.push("__other");

  if (columns.length === 0) return null;

  const count = (sev: FindingSeverity, col: string) =>
    findings.filter((f) => {
      const key = f.fieldOrKde ?? "";
      const inCol = col === "__other" ? !CTE_SHORT[key] : key === col;
      return f.severity === sev && inCol;
    }).length;

  const rows = SEVERITY_ROWS.filter((r) => findings.some((f) => f.severity === r.key));
  if (rows.length === 0) return null;

  const colLabel = (c: string) => (c === "__other" ? "Other" : (CTE_SHORT[c] ?? c));

  return (
    <Card padding="md">
      <h3 className="mb-3 text-sm font-semibold text-ink">Where the gaps are</h3>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th className="px-2 py-1.5 text-left text-xs font-semibold uppercase tracking-wide text-muted" />
              {columns.map((c) => (
                <th
                  key={c}
                  className="px-2 py-1.5 text-center text-xs font-semibold uppercase tracking-wide text-muted"
                >
                  {colLabel(c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td className="whitespace-nowrap px-2 py-1.5 text-sm font-medium text-ink">
                  {row.label}
                </td>
                {columns.map((c) => {
                  const n = count(row.key, c);
                  const cls = n === 0
                    ? "text-muted"
                    : row.tone === "risk"
                      ? "bg-risk-soft text-risk font-semibold"
                      : "bg-review-soft text-review font-semibold";
                  return (
                    <td key={c} className="px-1.5 py-1">
                      <div className={`grid h-9 place-items-center rounded-pill ${cls}`}>
                        {n === 0 ? "·" : n}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
