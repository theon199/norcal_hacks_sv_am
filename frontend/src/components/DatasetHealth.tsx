import type { DatasetSummary } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 font-mono text-lg">{value}</dd>
    </div>
  );
}

export function DatasetHealth({ summary }: { summary: DatasetSummary }) {
  const kinds = { numeric: 0, categorical: 0, unusable: 0 };
  for (const c of summary.columns) kinds[c.kind] += 1;
  const withMissing = summary.columns.filter((c) => c.missing_fraction > 0).length;

  return (
    <section className="rounded-lg border border-line p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-medium">
          {summary.filename}
          {summary.is_demo && (
            <span className="ml-2 rounded bg-accent-soft px-1.5 py-0.5 align-middle text-xs font-normal text-accent">
              example
            </span>
          )}
        </h2>
        <p className="font-mono text-xs text-muted" title={summary.sha256}>
          SHA-256 {summary.sha256.slice(0, 16)}…
        </p>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Rows" value={summary.n_rows.toLocaleString()} />
        <Stat label="Columns" value={String(summary.n_columns)} />
        <Stat label="Numeric" value={String(kinds.numeric)} />
        <Stat label="Categorical" value={String(kinds.categorical)} />
        <Stat label="With missing values" value={String(withMissing)} />
        <Stat label="Duplicate rows" value={String(summary.duplicate_row_count)} />
      </dl>

      <div className="mt-5 overflow-x-auto rounded-md border border-line">
        <table className="min-w-full text-left font-mono text-xs">
          <thead className="bg-surface text-muted">
            <tr>
              {summary.preview.columns.map((c) => (
                <th key={c} className="whitespace-nowrap px-3 py-2 font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {summary.preview.rows.map((row, i) => (
              <tr key={i} className="border-t border-line">
                {row.map((cell, j) => (
                  <td key={j} className="max-w-48 truncate whitespace-nowrap px-3 py-1.5">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">First {summary.preview.rows.length} rows shown.</p>
    </section>
  );
}
