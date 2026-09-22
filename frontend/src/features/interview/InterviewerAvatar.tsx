import { Icon } from "@/components/Icon";

/** A role emblem for the AI interviewer; no fabricated human identity or employer branding. */
export function InterviewerAvatar({
  icon = "mic",
  compact = false,
}: {
  icon?: string;
  compact?: boolean;
}) {
  return (
    <div
      aria-hidden
      className={`relative mx-auto grid place-items-center rounded-[28%] border border-[#a5d9c6]/25 bg-gradient-to-br from-[#49736b] to-[#263f43] shadow-[0_12px_50px_0_#0c202750] ${compact ? "h-20 w-20" : "h-36 w-36 sm:h-44 sm:w-44"}`}
    >
      <div className="absolute inset-2 rounded-[25%] border border-white/10" />
      <Icon
        name={icon}
        className={
          compact
            ? "h-8 w-8 text-[#d4eee3]"
            : "h-14 w-14 text-[#d4eee3] sm:h-16 sm:w-16"
        }
      />
      {!compact && (
        <span className="absolute -bottom-3 rounded-full border border-white/15 bg-[#213d3c] px-3 py-1 text-[10px] font-semibold tracking-[.18em] text-[#d4eee3]">
          AI INTERVIEWER
        </span>
      )}
    </div>
  );
}
