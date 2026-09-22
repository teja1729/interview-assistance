const MODES = [
  { id: "job", label: "Job", icon: "💼", ready: true },
  { id: "skill", label: "Skill", icon: "🛠", ready: false },
  { id: "coding", label: "Coding", icon: "</>", ready: false },
  { id: "system-design", label: "System Design", icon: "🗄", ready: false },
  { id: "behavioral", label: "Behavioral", icon: "🧭", ready: false },
  { id: "role-play", label: "Role Play", icon: "🎭", ready: false },
];

export function ModeTabs({ active = "job" }: { active?: string }) {
  return (
    <div
      className="flex flex-wrap gap-1 rounded-2xl bg-accent-soft/60 p-1"
      role="tablist"
      aria-label="Interview mode"
    >
      {MODES.map((m) => (
        <button
          key={m.id}
          role="tab"
          aria-selected={m.id === active}
          disabled={!m.ready}
          title={m.ready ? undefined : "Coming in a later phase"}
          className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm ${
            m.id === active
              ? "bg-accent text-accent-ink shadow-sm"
              : "text-muted"
          } ${m.ready ? "" : "cursor-not-allowed opacity-60"}`}
        >
          <span aria-hidden className="text-xs">
            {m.icon}
          </span>
          {m.label}
          {!m.ready && (
            <span className="ml-1 rounded-full border border-border px-1.5 text-[10px] uppercase">
              soon
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
