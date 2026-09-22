"use client";

import { useState } from "react";

type Point = { id: string; score: number; at: number; label: string };

/**
 * Score over time. Single series: 2px line, 8px markers, hover tooltip, no legend.
 * Text uses text tokens; the series color only carries the marks.
 */
export function ScoreChart({ points }: { points: Point[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 640;
  const H = 200;
  const pad = { l: 36, r: 16, t: 16, b: 28 };
  const sorted = [...points].sort((a, b) => a.at - b.at);

  if (sorted.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted">
        No finished interviews yet. Your score trend will appear here.
      </div>
    );
  }

  const xs = sorted.map((_, i) =>
    sorted.length === 1
      ? W / 2
      : pad.l + (i * (W - pad.l - pad.r)) / (sorted.length - 1),
  );
  const y = (s: number) => pad.t + (1 - s / 100) * (H - pad.t - pad.b);
  const path = xs
    .map(
      (x, i) =>
        `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y(sorted[i].score).toFixed(1)}`,
    )
    .join(" ");
  const h = hover !== null ? sorted[hover] : null;

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label="Interview score over time"
      >
        {[0, 25, 50, 75, 100].map((g) => (
          <g key={g}>
            <line
              x1={pad.l}
              x2={W - pad.r}
              y1={y(g)}
              y2={y(g)}
              stroke="var(--border)"
              strokeWidth={1}
            />
            <text
              x={pad.l - 8}
              y={y(g) + 4}
              textAnchor="end"
              fontSize={11}
              fill="var(--muted)"
            >
              {g}
            </text>
          </g>
        ))}
        {sorted.length > 1 && (
          <path
            d={path}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}
        {sorted.map((p, i) => (
          <g key={p.id}>
            {/* hit target larger than the mark */}
            <circle
              cx={xs[i]}
              cy={y(p.score)}
              r={14}
              fill="transparent"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            />
            <circle
              cx={xs[i]}
              cy={y(p.score)}
              r={hover === i ? 6 : 4}
              fill="var(--accent)"
              stroke="var(--surface)"
              strokeWidth={2}
              pointerEvents="none"
            />
          </g>
        ))}
        {sorted.length <= 8 &&
          sorted.map((p, i) => (
            <text
              key={p.id}
              x={xs[i]}
              y={H - 8}
              textAnchor="middle"
              fontSize={11}
              fill="var(--muted)"
            >
              {new Date(p.at * 1000).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}
            </text>
          ))}
      </svg>
      {h && hover !== null && (
        <div
          className="pointer-events-none absolute -translate-x-1/2 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs shadow"
          style={{
            left: `${(xs[hover] / W) * 100}%`,
            top: `${(y(h.score) / H) * 100 - 22}%`,
          }}
        >
          <div className="font-medium">{h.score} / 100</div>
          <div className="text-muted">{h.label}</div>
        </div>
      )}
    </div>
  );
}
