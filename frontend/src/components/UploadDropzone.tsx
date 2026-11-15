"use client";

import { useRef, useState } from "react";

export function UploadDropzone({ onFile, busy }: { onFile: (file: File) => void; busy: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file && !busy) onFile(file);
      }}
      className={`flex h-full flex-col justify-between gap-3 rounded-lg border border-dashed p-5 transition-colors ${
        over ? "border-accent bg-accent-soft" : "border-line"
      }`}
    >
      <div>
        <h3 className="font-medium">Audit your own claim</h3>
        <p className="mt-1 text-sm text-muted">
          Drop a CSV here or choose a file. Binary classification, tabular data, scikit-learn models. Up to 20 MB and
          100–5,000 rows; rows × feature columns up to 100,000 (for example 5,000 × 20 or 2,000 × 50).
        </p>
      </div>
      <div>
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => input.current?.click()}
          className="rounded-md border border-line px-3 py-1.5 text-sm font-medium hover:bg-surface disabled:opacity-50"
        >
          Choose CSV
        </button>
        <p className="mt-3 text-xs text-muted">
          Do not upload confidential or personal data. Files are deleted within 24 hours.
        </p>
      </div>
    </div>
  );
}
