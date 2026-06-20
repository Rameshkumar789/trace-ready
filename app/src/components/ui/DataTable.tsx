import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "./cn";

export type Column<Row> = {
  key: string;
  header: ReactNode;
  /** Cell renderer. */
  cell: (row: Row) => ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
};

export function DataTable<Row>({
  columns,
  rows,
  rowKey,
  rowHref,
  empty,
  className,
}: {
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  rowHref?: (row: Row) => string | undefined;
  empty?: ReactNode;
  className?: string;
}) {
  const alignClass = (a?: "left" | "right" | "center") =>
    a === "right" ? "text-right" : a === "center" ? "text-center" : "text-left";

  if (rows.length === 0 && empty) {
    return <>{empty}</>;
  }

  return (
    <div
      className={cn(
        "overflow-hidden rounded-card border border-line bg-panel shadow-sm",
        className,
      )}
    >
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line bg-surface">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted",
                  alignClass(col.align),
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const href = rowHref?.(row);
            return (
              <tr
                key={rowKey(row)}
                className={cn(
                  "border-b border-line last:border-0",
                  href && "transition-colors hover:bg-surface-strong",
                )}
              >
                {columns.map((col) => {
                  const content = col.cell(row);
                  return (
                    <td
                      key={col.key}
                      className={cn("px-4 py-3 text-ink", alignClass(col.align), col.className)}
                    >
                      {href ? (
                        <Link href={href} className="block">
                          {content}
                        </Link>
                      ) : (
                        content
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
