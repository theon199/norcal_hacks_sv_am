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
      className={`flex flex-col gap-4 rounded-[14px] border-2 border-dashed p-5 transition-colors sm:flex-row sm:items-center sm:justify-between sm:gap-8 ${
        over ? "border-accent bg-accent-soft" : "border-line"
      }`}
    >
      <div className="max-w-2xl">
        <h3 className="font-semibold">Audit your own claim</h3>
        <p className="mt-1 text-sm text-muted">
          Drop a CSV here or choose a file. Binary classification, tabular data, scikit-learn models. Up to 20 MB and
          100–5,000 rows; rows × feature columns up to 100,000 (for example 5,000 × 20 or 2,000 × 50).
        </p>
        <p className="mt-2 text-xs text-muted">
          Do not upload confidential or personal data. Files are deleted within 24 hours.
        </p>
      </div>
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
      <button type="button" disabled={busy} onClick={() => input.current?.click()} className="btn shrink-0 self-start sm:self-center">
        Choose CSV
      </button>
    </div>
  );
}
