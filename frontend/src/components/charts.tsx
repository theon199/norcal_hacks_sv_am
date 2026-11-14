"use client";

// Hand-written SVG charts. Every number drawn here comes straight from the backend report.
// Accuracy is shown in percent; lift is shown in percentage points. They never share an axis.

import { useEffect, useRef, useState, type ReactNode } from "react";

import { pct, pp } from "@/lib/format";
import type { NoiseResult, SplitResult } from "@/lib/types";

const INK = "var(--foreground)";
const MUTED = "var(--muted)";
const GRID = "var(--chart-grid)";
const S1 = "var(--series-1)"; // candidate
const S2 = "var(--series-2)"; // baseline

function useWidth(): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.floor(entry.contentRect.width))));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

function niceTicks(min: number, max: number, target = 5): number[] {
  const span = max - min || 1;
  const raw = span / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= target + 1) ?? 10 * mag;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-6; v += step) ticks.push(Number(v.toFixed(6)));
  return ticks;
}

function accuracy(run: SplitResult, role: "candidate" | "baseline"): number {
  return run.scores.find((s) => s.model === role)!.accuracy;
}

function splitLabel(run: SplitResult, isDefault: boolean, narrow = false): string {
  if (narrow) return String(run.seed); // the axis caption explains which seed is the default
  return isDefault ? `Default (${run.seed})` : `Seed ${run.seed}`;
}

function SeedAxisCaption({ width, y, defaultSeed }: { width: number; y: number; defaultSeed: number }) {
  return (
    <text x={width / 2} y={y} textAnchor="middle" fontSize="11" fill={MUTED}>
      split seed ({defaultSeed} = default split)
    </text>
  );
}

function Legend({ items }: { items: { swatch: ReactNode; label: string }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <svg width="18" height="12" aria-hidden="true">
            {item.swatch}
          </svg>
          {item.label}
        </li>
      ))}
    </ul>
  );
}

function Frame({ title, subtitle, legend, note, children }: {
  title: string;
  subtitle: string;
  legend?: ReactNode;
  note?: string;
  children: ReactNode;
}) {
  return (
    <figure className="rounded-lg border border-line p-4 sm:p-5">
      <figcaption>
        <h3 className="font-medium">{title}</h3>
        <p className="mt-0.5 text-sm text-muted">{subtitle}</p>
      </figcaption>
      {legend && <div className="mt-3">{legend}</div>}
      <div className="mt-2">{children}</div>
      {note && <p className="mt-2 text-xs text-muted">{note}</p>}
    </figure>
  );
}

/** Lift per split, in percentage points, on a zero baseline with the claimed threshold marked. */
export function LiftChart({ defaultSplit, seedRuns, thresholdPp }: {
  defaultSplit: SplitResult;
  seedRuns: SplitResult[];
  thresholdPp: number;
}) {
  const [ref, width] = useWidth();
  const runs = [defaultSplit, ...seedRuns];
  const narrow = width < 520;
  const height = 280;
  const m = { top: 24, right: 16, bottom: narrow ? 52 : 44, left: narrow ? 40 : 48 };
  const lifts = runs.map((r) => r.lift_pp);
  const lo = Math.min(0, ...lifts);
  const hi = Math.max(thresholdPp, ...lifts);
  const pad = (hi - lo) * 0.15 || 1;
  const yMin = lo < 0 ? lo - pad : 0;
  const yMax = hi + pad;
  const y = (v: number) => m.top + ((yMax - v) / (yMax - yMin)) * (height - m.top - m.bottom);
  const band = (width - m.left - m.right) / runs.length;
  const barW = Math.min(24, band * 0.5);
  const sep = m.left + band; // divider between the default split and the five repeats

  return (
    <Frame
      title="Lift on each split"
      subtitle="Candidate accuracy minus baseline accuracy, in percentage points (pp). Zero means no difference."
      legend={
        <Legend
          items={[
            { swatch: <rect x="3" y="1" width="12" height="10" rx="2" fill={S1} />, label: "Meets the claimed threshold" },
            {
              swatch: <rect x="3.75" y="1.75" width="10.5" height="8.5" rx="2" fill="none" stroke={MUTED} strokeWidth="1.5" />,
              label: "Below the threshold",
            },
            {
              swatch: <line x1="0" y1="6" x2="18" y2="6" stroke={INK} strokeWidth="1.5" strokeDasharray="4 3" />,
              label: `Claimed threshold (${pp(thresholdPp)})`,
            },
          ]}
        />
      }
    >
      <div ref={ref}>
        <svg width={width} height={height} role="img" aria-label="Bar chart of lift in percentage points for each split">
          {niceTicks(yMin, yMax).map((t) => (
            <g key={t}>
              <line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} stroke={GRID} strokeWidth={t === 0 ? 0 : 1} />
              <text x={m.left - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill={MUTED}>
                {t}
              </text>
            </g>
          ))}
          <text x={12} y={m.top - 10} fontSize="11" fill={MUTED}>
            lift (pp)
          </text>
          <line x1={sep} x2={sep} y1={m.top} y2={height - m.bottom + 24} stroke={GRID} strokeDasharray="2 3" />
          {runs.map((run, i) => {
            const cx = m.left + band * (i + 0.5);
            const top = Math.min(y(run.lift_pp), y(0));
            const h = Math.max(1, Math.abs(y(run.lift_pp) - y(0)));
            const label = splitLabel(run, i === 0);
            const above = run.lift_pp >= 0;
            return (
              <g key={run.seed}>
                <rect
                  x={cx - barW / 2}
                  y={top}
                  width={barW}
                  height={h}
                  rx={Math.min(4, h / 2)}
                  fill={run.meets_threshold ? S1 : "transparent"}
                  stroke={run.meets_threshold ? "none" : MUTED}
                  strokeWidth="1.5"
                />
                <text x={cx} y={above ? top - 6 : top + h + 14} textAnchor="middle" fontSize="11" fill={INK}>
                  {pp(run.lift_pp)}
                </text>
                <text x={cx} y={height - m.bottom + 18} textAnchor="middle" fontSize="11" fill={MUTED}>
                  {splitLabel(run, i === 0, narrow)}
                </text>
                <rect x={cx - band / 2} y={m.top} width={band} height={height - m.top - m.bottom} fill="transparent">
                  <title>
                    {`${label}: lift ${pp(run.lift_pp, 2)} (candidate ${pct(accuracy(run, "candidate"), 2)}, baseline ${pct(
                      accuracy(run, "baseline"),
                      2,
                    )}). ${run.meets_threshold ? "Meets" : "Does not meet"} the claimed ${pp(thresholdPp)}.`}
                  </title>
                </rect>
              </g>
            );
          })}
          {narrow && <SeedAxisCaption width={width} y={height - 8} defaultSeed={defaultSplit.seed} />}
          <line x1={m.left} x2={width - m.right} y1={y(0)} y2={y(0)} stroke={INK} strokeWidth="1" />
          <line
            x1={m.left}
            x2={width - m.right}
            y1={y(thresholdPp)}
            y2={y(thresholdPp)}
            stroke={INK}
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />
        </svg>
      </div>
    </Frame>
  );
}

/** Paired accuracy of both models on each split. Dot plot, so a non-zero axis start is legitimate — and stated. */
export function AccuracyChart({ defaultSplit, seedRuns, candidateLabel, baselineLabel }: {
  defaultSplit: SplitResult;
  seedRuns: SplitResult[];
  candidateLabel: string;
  baselineLabel: string;
}) {
  const [ref, width] = useWidth();
  const runs = [defaultSplit, ...seedRuns];
  const narrow = width < 520;
  const height = 260;
  const m = { top: 24, right: 16, bottom: narrow ? 52 : 44, left: narrow ? 40 : 48 };
  const values = runs.flatMap((r) => [accuracy(r, "candidate"), accuracy(r, "baseline")]).map((v) => v * 100);
  const yMin = Math.max(0, Math.floor((Math.min(...values) - 2) / 5) * 5);
  const yMax = 100;
  const y = (v: number) => m.top + ((yMax - v) / (yMax - yMin)) * (height - m.top - m.bottom);
  const band = (width - m.left - m.right) / runs.length;
  const sep = m.left + band;

  return (
    <Frame
      title="Accuracy of both models on each split"
      subtitle="Test-set accuracy (%). Both models are fitted and scored on the same rows within each split."
      legend={
        <Legend
          items={[
            { swatch: <circle cx="9" cy="6" r="5" fill={S1} />, label: `${candidateLabel} (candidate)` },
            { swatch: <rect x="4.5" y="1.5" width="9" height="9" fill={S2} transform="rotate(45 9 6)" />, label: `${baselineLabel} (baseline)` },
          ]}
        />
      }
      note={yMin > 0 ? `The vertical axis starts at ${yMin}%, not 0, so that small differences are visible.` : undefined}
    >
      <div ref={ref}>
        <svg width={width} height={height} role="img" aria-label="Dot plot of candidate and baseline accuracy for each split">
          {niceTicks(yMin, yMax).map((t) => (
            <g key={t}>
              <line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} stroke={GRID} />
              <text x={m.left - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill={MUTED}>
                {t}
              </text>
            </g>
          ))}
          <text x={12} y={m.top - 10} fontSize="11" fill={MUTED}>
            accuracy (%)
          </text>
          <line x1={sep} x2={sep} y1={m.top} y2={height - m.bottom + 24} stroke={GRID} strokeDasharray="2 3" />
          {runs.map((run, i) => {
            const cx = m.left + band * (i + 0.5);
            const c = accuracy(run, "candidate") * 100;
            const b = accuracy(run, "baseline") * 100;
            const label = splitLabel(run, i === 0);
            const off = Math.abs(y(c) - y(b)) < 10 ? 7 : 0; // nudge apart when the two marks would overlap
            return (
              <g key={run.seed}>
                <line x1={cx} x2={cx} y1={y(c)} y2={y(b)} stroke={MUTED} strokeWidth="1.5" />
                <rect
                  x={cx + off - 5}
                  y={y(b) - 5}
                  width="10"
                  height="10"
                  fill={S2}
                  stroke="var(--background)"
                  strokeWidth="2"
                  transform={`rotate(45 ${cx + off} ${y(b)})`}
                />
                <circle cx={cx - off} cy={y(c)} r="6" fill={S1} stroke="var(--background)" strokeWidth="2" />
                <text x={cx} y={height - m.bottom + 18} textAnchor="middle" fontSize="11" fill={MUTED}>
                  {splitLabel(run, i === 0, narrow)}
                </text>
                <rect x={cx - band / 2} y={m.top} width={band} height={height - m.top - m.bottom} fill="transparent">
                  <title>
                    {`${label}: ${candidateLabel} ${pct(c / 100, 2)}, ${baselineLabel} ${pct(b / 100, 2)}, on ${run.n_test} test rows.`}
                  </title>
                </rect>
              </g>
            );
          })}
          {narrow && <SeedAxisCaption width={width} y={height - 8} defaultSeed={defaultSplit.seed} />}
        </svg>
      </div>
    </Frame>
  );
}

/** Clean vs noisy accuracy for each model on the default split, with the range across draws. */
export function NoiseChart({ noise, candidateLabel, baselineLabel }: {
  noise: NoiseResult;
  candidateLabel: string;
  baselineLabel: string;
}) {
  const [ref, width] = useWidth();
  const rows = noise.per_model.map((p) => ({
    ...p,
    name: p.model === "candidate" ? candidateLabel : baselineLabel,
    color: p.model === "candidate" ? S1 : S2,
  }));
  const rowH = 56;
  const m = { top: 12, right: 24, bottom: 36, left: width < 480 ? 96 : 150 };
  const height = m.top + rows.length * rowH + m.bottom;
  const all = rows.flatMap((r) => [r.clean_accuracy, r.noisy_min, r.noisy_max]).map((v) => v * 100);
  const xMin = Math.max(0, Math.floor((Math.min(...all) - 2) / 5) * 5);
  const xMax = 100;
  const x = (v: number) => m.left + ((v - xMin) / (xMax - xMin)) * (width - m.left - m.right);

  return (
    <Frame
      title="Accuracy under feature noise"
      subtitle={`Default-split models scored on test rows with Gaussian noise added to ${noise.perturbed_features.length} numeric feature(s): ${Math.round(
        noise.noise_scale * 100,
      )}% of each feature's training standard deviation, ${noise.n_draws} seeded draws. Models are not refitted.`}
      legend={
        <Legend
          items={[
            { swatch: <circle cx="9" cy="6" r="4.25" fill="var(--background)" stroke={INK} strokeWidth="1.5" />, label: "Clean test data" },
            { swatch: <circle cx="9" cy="6" r="5" fill={INK} />, label: `Mean of ${noise.n_draws} noisy draws` },
            { swatch: <line x1="1" y1="6" x2="17" y2="6" stroke={INK} strokeWidth="2" />, label: "Lowest to highest draw" },
          ]}
        />
      }
      note={`${xMin > 0 ? `The axis starts at ${xMin}%, not 0. ` : ""}This is one specific noise model, not a claim about real-world measurement error.`}
    >
      <div ref={ref}>
        <svg width={width} height={height} role="img" aria-label="Clean and noisy accuracy for each model">
          {niceTicks(xMin, xMax).map((t) => (
            <g key={t}>
              <line x1={x(t)} x2={x(t)} y1={m.top} y2={height - m.bottom} stroke={GRID} />
              <text x={x(t)} y={height - m.bottom + 16} textAnchor="middle" fontSize="11" fill={MUTED}>
                {t}
              </text>
            </g>
          ))}
          <text x={width - m.right} y={height - 4} textAnchor="end" fontSize="11" fill={MUTED}>
            accuracy (%)
          </text>
          {rows.map((r, i) => {
            const cy = m.top + rowH * (i + 0.5);
            return (
              <g key={r.model}>
                <rect x={8} y={cy - 16} width="4" height="32" rx="2" fill={r.color} />
                <text x={18} y={cy - 2} fontSize="12" fill={INK}>
                  {r.name}
                </text>
                <text x={18} y={cy + 13} fontSize="11" fill={MUTED}>
                  {pp(r.delta_pp)} under noise
                </text>
                <line x1={x(r.noisy_min * 100)} x2={x(r.noisy_max * 100)} y1={cy} y2={cy} stroke={r.color} strokeWidth="2" strokeLinecap="round" />
                <circle cx={x(r.noisy_mean_accuracy * 100)} cy={cy} r="6" fill={r.color} stroke="var(--background)" strokeWidth="2" />
                <circle cx={x(r.clean_accuracy * 100)} cy={cy} r="5.25" fill="var(--background)" stroke={r.color} strokeWidth="2" />
                <rect x={m.left} y={cy - rowH / 2} width={width - m.left - m.right} height={rowH} fill="transparent">
                  <title>
                    {`${r.name}: clean ${pct(r.clean_accuracy, 2)}; noisy mean ${pct(r.noisy_mean_accuracy, 2)} (lowest ${pct(
                      r.noisy_min,
                      2,
                    )}, highest ${pct(r.noisy_max, 2)}); change ${pp(r.delta_pp, 2)}.`}
                  </title>
                </rect>
              </g>
            );
          })}
        </svg>
      </div>
    </Frame>
  );
}
