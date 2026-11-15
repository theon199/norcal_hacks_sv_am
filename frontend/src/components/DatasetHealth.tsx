import type { DatasetSummary } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card px-4 py-3">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-xl font-semibold tabular-nums tracking-tight">{value}</dd>
    </div>
  );
}

export function DatasetHealth({ summary }: { summary: DatasetSummary }) {
  const kinds = { numeric: 0, categorical: 0, unusable: 0 };
  for (const c of summary.columns) kinds[c.kind] += 1;
  const withMissing = summary.columns.filter((c) => c.missing_fraction > 0).length;

  return (
    <section className="card overflow-hidden">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5">
        <h3 className="flex flex-wrap items-center gap-2 text-lg font-semibold tracking-tight">
          <span className="break-all">{summary.filename}</span>
          {summary.is_demo && <span className="tag">example</span>}
        </h3>
        <p className="font-mono text-xs text-muted" title={summary.sha256}>
          SHA-256 {summary.sha256.slice(0, 16)}…
        </p>
      </div>
      {/* The 1px gaps over a line-coloured background draw the dividers between stats. */}
      <dl className="mt-4 grid grid-cols-2 gap-px border-y border-line bg-line sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Rows" value={summary.n_rows.toLocaleString()} />
        <Stat label="Columns" value={String(summary.n_columns)} />
        <Stat label="Numeric" value={String(kinds.numeric)} />
        <Stat label="Categorical" value={String(kinds.categorical)} />
        <Stat label="With missing values" value={String(withMissing)} />
        <Stat label="Duplicate rows" value={String(summary.duplicate_row_count)} />
      </dl>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs tabular-nums">
          <thead className="bg-surface text-muted">
            <tr>
              {summary.preview.columns.map((c) => (
                <th key={c} className="whitespace-nowrap px-4 py-2 font-mono font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {summary.preview.rows.map((row, i) => (
              <tr key={i} className="border-t border-line">
                {row.map((cell, j) => (
                  <td key={j} className="max-w-48 truncate whitespace-nowrap px-4 py-1.5">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t border-line px-5 py-2.5 text-xs text-muted">First {summary.preview.rows.length} rows shown.</p>
    </section>
  );
}
