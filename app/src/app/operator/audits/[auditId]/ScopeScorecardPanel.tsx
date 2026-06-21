import { Layers3, ClipboardCheck } from "lucide-react";
import { Card, SectionHeader } from "@/components/ui";
import type { StoredAudit } from "@/lib/audit/stored-audit";
import {
  buildSupplierProductCoverage,
  buildSupplierScorecards,
  type SupplierProductCoverageRow,
  type SupplierScorecardRow,
} from "@/lib/report/supplier-scorecard";

const STATUS_STYLE: Record<SupplierProductCoverageRow["status"], { label: string; bg: string; fg: string }> = {
  gap: { label: "GAP", bg: "#FBE9E6", fg: "#B42318" },
  covered: { label: "ok", bg: "#E7F4EE", fg: "#117A57" },
  out_of_scope: { label: "off-list", bg: "#EEF1F4", fg: "#5C6672" },
};

const GRADE_STYLE: Record<SupplierScorecardRow["grade"], { bg: string; fg: string }> = {
  A: { bg: "#E7F4EE", fg: "#117A57" },
  B: { bg: "#E7F4EE", fg: "#117A57" },
  C: { bg: "#FBEFD6", fg: "#7A4F00" },
  D: { bg: "#FBE9E6", fg: "#B42318" },
  F: { bg: "#FBE9E6", fg: "#B42318" },
};

export function ScopeScorecardPanel({ audit }: { audit: StoredAudit }) {
  const coverage = buildSupplierProductCoverage(audit);
  const scorecards = buildSupplierScorecards(audit);
  if (!coverage.length && !scorecards.length) return null;

  return (
    <div className="flex flex-col gap-6">
      {coverage.length ? (
        <section className="flex flex-col gap-3">
          <SectionHeader
            icon={<Layers3 size={18} />}
            title="Scope — supplier × product"
            count={coverage.length}
            hint="Which suppliers and products to worry about"
          />
          <Card padding="lg">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="text-left text-muted">
                    <th className="py-2 pr-3 font-semibold">Supplier</th>
                    <th className="py-2 pr-3 font-semibold">Product</th>
                    <th className="py-2 pr-3 font-semibold">FTL</th>
                    <th className="py-2 pr-3 font-semibold">Events</th>
                    <th className="py-2 pr-3 font-semibold">Gaps</th>
                    <th className="py-2 pr-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {coverage.map((row) => {
                    const style = STATUS_STYLE[row.status];
                    return (
                      <tr key={`${row.supplierId}::${row.product}`} className="border-t border-line">
                        <td className="py-2 pr-3 text-ink">{row.supplierId}</td>
                        <td className="py-2 pr-3 text-ink">{row.product}</td>
                        <td className="py-2 pr-3 text-muted">{row.ftlStatus}</td>
                        <td className="py-2 pr-3 text-muted">{row.eventCount}</td>
                        <td className="py-2 pr-3 text-muted">
                          {row.gapCount}
                          {row.tlcGap ? <span style={{ color: "#B42318", fontWeight: 600 }}> · TLC</span> : null}
                        </td>
                        <td className="py-2 pr-3">
                          <span
                            className="inline-block rounded px-2 py-0.5 text-xs font-semibold"
                            style={{ background: style.bg, color: style.fg }}
                          >
                            {style.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </section>
      ) : null}

      {scorecards.length ? (
        <section className="flex flex-col gap-3">
          <SectionHeader
            icon={<ClipboardCheck size={18} />}
            title="Supplier scorecards"
            count={scorecards.length}
            hint="Hand these to suppliers — graded, with required actions"
          />
          <div className="grid gap-3 md:grid-cols-2">
            {scorecards.map((card) => {
              const g = GRADE_STYLE[card.grade];
              return (
                <Card key={card.supplierId} padding="lg">
                  <div className="flex items-center gap-3">
                    <span
                      className="grid h-9 w-9 place-items-center rounded-lg text-base font-extrabold"
                      style={{ background: g.bg, color: g.fg }}
                    >
                      {card.grade}
                    </span>
                    <div className="flex flex-col">
                      <span className="font-semibold text-ink">{card.supplierId}</span>
                      <span className="text-xs text-muted">
                        {card.productsWithGaps}/{card.inScopeProducts} products with gaps
                        {card.tlcGap ? " · TLC broken" : ""}
                      </span>
                    </div>
                  </div>
                  {card.recommendedActions.length ? (
                    <ul className="mt-3 flex flex-col gap-1.5 text-sm text-muted">
                      {card.recommendedActions.map((action, i) => (
                        <li key={i}>→ {action.action}</li>
                      ))}
                    </ul>
                  ) : null}
                </Card>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}
