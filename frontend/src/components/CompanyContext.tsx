import type { CompanyBrief } from "@/lib/api";

/** Only source-backed facts are shown. Search Suggestions are isolated in a script-free frame. */
export function CompanyContext({
  brief,
  dark = false,
}: {
  brief?: CompanyBrief;
  dark?: boolean;
}) {
  if (!brief || brief.status === "not_requested") return null;
  return (
    <details
      className={`rounded-xl border p-4 text-left text-sm ${dark ? "border-white/15 bg-white/5 text-white/85" : "border-border bg-surface"}`}
      open={!dark}
    >
      <summary className="cursor-pointer font-medium">
        {brief.status === "researched"
          ? `Research for ${brief.company}`
          : "Company research unavailable"}
      </summary>
      <p className="mt-2 text-xs opacity-75">{brief.note}</p>
      {brief.researched_at && (
        <p className="mt-1 text-xs opacity-65">
          Researched {new Date(brief.researched_at * 1000).toLocaleDateString()}
          {brief.cached ? " · Loaded from saved research" : ""}
        </p>
      )}
      <ul className="mt-3 space-y-3">
        {brief.facts.map((fact, i) => (
          <li key={i} className="text-xs leading-6">
            {fact.text}{" "}
            {fact.source_ids.map((id) => {
              const source = brief.sources.find((s) => s.id === id);
              return (
                source && (
                  <a
                    key={id}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`ml-1 underline ${dark ? "text-[#a5d9c6]" : "text-accent"}`}
                  >
                    {source.title}
                  </a>
                )
              );
            })}
          </li>
        ))}
      </ul>
      {brief.search_suggestions && (
        <iframe
          title="Google Search suggestions"
          srcDoc={brief.search_suggestions}
          sandbox="allow-popups allow-popups-to-escape-sandbox"
          referrerPolicy="no-referrer"
          className="mt-3 h-28 w-full rounded-lg border-0 bg-white"
        />
      )}
    </details>
  );
}
