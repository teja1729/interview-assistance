const MODES = [
  { id: "voice", label: "Voice interview", icon: "🎙" },
  { id: "text", label: "Text topic practice", icon: "✎" },
];

export function ModeTabs({
  active,
  onChange,
}: {
  active: "voice" | "text";
  onChange: (mode: "voice" | "text") => void;
}) {
  return (
    <div
      className="flex flex-wrap gap-1 rounded-2xl bg-accent-soft/60 p-1"
      role="group"
      aria-label="Interview mode"
    >
      {MODES.map((m) => (
        <button
          key={m.id}
          aria-pressed={m.id === active}
          type="button"
          onClick={() => onChange(m.id as "voice" | "text")}
          className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm ${
            m.id === active
              ? "bg-accent text-accent-ink shadow-sm"
              : "text-muted"
          }`}
        >
          <span aria-hidden className="text-xs">
            {m.icon}
          </span>
          {m.label}
        </button>
      ))}
    </div>
  );
}
