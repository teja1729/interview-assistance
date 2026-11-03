"use client";

import styles from "./Waveform.module.css";

interface WaveformProps {
  bars?: number;
  active?: boolean;
  height?: number;
  spectral?: boolean;
  className?: string;
}

const SPECTRAL_COLORS = [
  "#7C3AED",
  "#6D28D9",
  "#4F46E5",
  "#2563EB",
  "#0284C7",
  "#0891B2",
  "#0D9488",
  "#059669",
  "#16A34A",
  "#65A30D",
  "#84CC16",
  "#CA8A04",
  "#D97706",
  "#EA580C",
  "#DC2626",
];

// Deterministic heights to avoid hydration mismatch
const BAR_HEIGHTS = [
  0.3, 0.6, 0.45, 0.8, 0.55, 0.9, 0.4, 0.7, 0.5, 0.85, 0.35, 0.65, 0.75, 0.5,
  0.4, 0.9, 0.6, 0.45, 0.8, 0.55, 0.3, 0.7, 0.5, 0.85, 0.4, 0.65, 0.75, 0.5,
  0.4, 0.9, 0.6, 0.45, 0.8, 0.35, 0.7, 0.5, 0.85, 0.45, 0.65, 0.75,
];

export default function Waveform({
  bars = 24,
  active = false,
  height = 64,
  spectral = false,
  className = "",
}: WaveformProps) {
  return (
    <div
      className={`${styles.container} ${className}`}
      style={{ height, gap: 3 }}
      aria-hidden="true"
      role="presentation"
    >
      {Array.from({ length: bars }).map((_, i) => {
        const ratio = i / (bars - 1);
        const colorIdx = Math.floor(ratio * (SPECTRAL_COLORS.length - 1));
        const barHeight = BAR_HEIGHTS[i % BAR_HEIGHTS.length];
        const color = spectral
          ? SPECTRAL_COLORS[colorIdx]
          : "var(--text-primary)";

        return (
          <div
            key={i}
            className={`${styles.bar} ${active ? styles.active : ""}`}
            style={{
              height: `${barHeight * 100}%`,
              background: color,
              opacity: spectral ? 0.75 : active ? 0.85 : 0.25,
              animationDelay: `${(i * 0.08) % 0.7}s`,
              width: 3,
            }}
          />
        );
      })}
    </div>
  );
}
