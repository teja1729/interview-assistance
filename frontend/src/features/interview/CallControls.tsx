import { fmtClock } from "@/lib/api";
/* ------------------------------------------------------------ pieces */

export function TopBar({
  clock,
  title,
  company,
  remaining,
}: {
  clock: string;
  title: string;
  company: string;
  remaining: number | null;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-6 pt-4 text-sm">
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        <span className="tabular-nums text-white/90">{clock}</span>
        <span className="text-white/30">|</span>
        <span className="font-medium">{title}</span>
        {company && <span className="text-white/60">· {company}</span>}
      </div>
      {remaining !== null && (
        <div
          className={`rounded-full px-3 py-1 font-mono text-sm tabular-nums ${remaining <= 120 ? "bg-[#ea4335]/20 text-[#f28b82]" : "bg-white/10 text-white/80"}`}
        >
          {fmtClock(remaining)} left
        </div>
      )}
    </div>
  );
}

export function RoundBtn({
  on,
  active,
  disabled,
  onClick,
  label,
  icon,
}: {
  on: boolean;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  label: string;
  icon: React.ReactNode;
}) {
  // active: blue (doing something now). on: neutral gray. off: red, like a muted control in Meet.
  const tone = active
    ? "bg-[#8ab4f8] text-[#202124]"
    : on
      ? "bg-[#3c4043] text-white hover:bg-[#4a4d51]"
      : "bg-[#ea4335]/90 text-white hover:bg-[#ea4335]";
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-pressed={on}
      title={label}
      className={`flex h-12 w-12 items-center justify-center rounded-full transition disabled:opacity-40 ${tone}`}
    >
      {icon}
    </button>
  );
}

export function SpeakingBars() {
  return (
    <div className="absolute -bottom-11 left-1/2 flex -translate-x-1/2 items-end gap-1 rounded-full bg-[#a5d9c6] px-2 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="block w-1 animate-bounce rounded-full bg-[#202124]"
          style={{
            height: 10,
            animationDelay: `${i * 120}ms`,
            animationDuration: "900ms",
          }}
        />
      ))}
    </div>
  );
}

/* icons: 24px Material-style outlines */
const I = ({ d, className = "h-6 w-6" }: { d: string; className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    fill="currentColor"
    aria-hidden
  >
    <path d={d} />
  </svg>
);
export const MicIcon = ({ className }: { className?: string }) => (
  <I
    className={className}
    d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z"
  />
);
export const MicOffIcon = ({ className }: { className?: string }) => (
  <I
    className={className}
    d="M19 11h-1.7c0 .74-.16 1.43-.43 2.05l1.23 1.23A6.9 6.9 0 0 0 19 11zM4.27 3 3 4.27l6 6V11a3 3 0 0 0 3 3c.4 0 .78-.09 1.13-.23l1.66 1.66A6.9 6.9 0 0 1 12 16a7 7 0 0 1-7-5H3a9 9 0 0 0 8 6.92V21h2v-3.08a8.9 8.9 0 0 0 3.02-1.07L19.73 21 21 19.73 4.27 3zM15 11V5a3 3 0 0 0-6 0v.18l6 6V11z"
  />
);
export const CamIcon = () => (
  <I d="M17 10.5V7a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3.5l4 4v-11l-4 4z" />
);
export const CamOffIcon = () => (
  <I d="M21 6.5l-4 4V7a1 1 0 0 0-1-1H9.82L21 17.18V6.5zM3.27 2 2 3.27 4.73 6H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12c.21 0 .39-.08.54-.18L19.73 21 21 19.73 3.27 2z" />
);
export const CcIcon = () => (
  <I d="M19 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm-8 7H9.5v-.5h-2v3h2V13H11v1a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v1zm7 0h-1.5v-.5h-2v3h2V13H18v1a1 1 0 0 1-1 1h-3a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v1z" />
);
export const KeyboardIcon = () => (
  <I d="M20 5H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm-9 3h2v2h-2V8zm0 3h2v2h-2v-2zM8 8h2v2H8V8zm0 3h2v2H8v-2zm-1 2H5v-2h2v2zm0-3H5V8h2v2zm9 7H8v-2h8v2zm0-4h-2v-2h2v2zm0-3h-2V8h2v2zm3 3h-2v-2h2v2zm0-3h-2V8h2v2z" />
);
export const ChatIcon = () => (
  <I d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z" />
);
export const EndIcon = () => (
  <I d="M12 9c-1.6 0-3.15.25-4.6.72v3.1c0 .39-.23.74-.56.9-.98.49-1.87 1.12-2.66 1.85-.18.18-.43.28-.7.28-.28 0-.53-.11-.71-.29L.29 13.08a.956.956 0 0 1-.29-.7c0-.28.11-.53.29-.71C3.34 8.78 7.46 7 12 7s8.66 1.78 11.71 4.67c.18.18.29.43.29.71 0 .27-.11.52-.29.7l-2.48 2.48c-.18.18-.43.29-.71.29-.27 0-.52-.1-.7-.28a11.27 11.27 0 0 0-2.66-1.85.995.995 0 0 1-.56-.9v-3.1C15.15 9.25 13.6 9 12 9z" />
);
export const CloseIcon = () => (
  <I
    className="h-5 w-5"
    d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
  />
);
