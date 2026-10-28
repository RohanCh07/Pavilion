// Rules & Scoring: the design's "Series Fantasy Rules" widget, expanded to the full ruleset.
import { useState } from "react";
import { api } from "../api";
import { Icon } from "../components/Icon";
import { ErrorBox, Segmented, Skeletons } from "../components/ui";
import { FORMAT_LABEL } from "../format";
import { useData } from "../hooks";

export function Rules() {
  const rules = useData(() => api.rules(), []);
  const [fmt, setFmt] = useState("t20");
  if (rules.loading && !rules.data) return <Skeletons rows={3} height={200} />;
  if (rules.error && !rules.data) return <ErrorBox message={rules.error} onRetry={() => rules.reload(true)} />;
  const r = rules.data!;
  const formats = r.formats.length ? r.formats : [{ format: "t20", name: r.name, sections: r.sections }];
  const current = formats.find((f) => f.format === fmt) ?? formats[0];

  return (
    <div className="flex w-full flex-col gap-space-xl">
      <div className="flex flex-col">
        <div className="mb-space-2xs flex items-center gap-space-xs text-outline">
          <span className="font-label-meta text-label-meta font-semibold tracking-wider uppercase">Scoring Rubric</span>
          <span className="font-label-meta text-label-meta">•</span>
          <span className="font-label-numeric text-label-numeric font-medium text-primary">v{r.version}</span>
        </div>
        <h1 className="font-headline-xl-mobile text-headline-xl-mobile tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">Rules &amp; Scoring</h1>
        <p className="mt-space-2xs max-w-2xl font-body-md text-body-md text-on-surface-variant">
          Points are worked out from each player's real scorecard. Each match uses the rules for its
          format: T20, ODI or Test.
        </p>
      </div>

      <div className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
        <div className="flex items-center gap-space-xs">
          <Icon name="fact_check" className="text-[20px] text-outline" />
          <h2 className="font-headline-md text-[18px] font-bold text-on-surface">Team Rules</h2>
        </div>
        <div className="flex flex-col gap-space-sm font-body-sm text-body-sm text-on-surface-variant">
          <div className="flex items-start gap-space-sm rounded-lg bg-surface-container-low p-space-xs">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-container font-label-numeric text-[11px] font-bold text-on-surface">1</span>
            <div>
              <strong className="font-semibold text-on-surface">
                {r.team_min_players === r.team_max_players ? r.team_max_players : `${r.team_min_players}-${r.team_max_players}`} Players per Roster
              </strong>
              <p className="mt-0.5 text-[13px] text-outline">Pick from the series squads, or the two sides of one match.</p>
            </div>
          </div>
          <div className="flex items-start gap-space-sm rounded-lg bg-surface-container-low p-space-xs">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-container font-label-numeric text-[11px] font-bold text-on-surface">2</span>
            <div>
              <strong className="font-semibold text-on-surface">Multipliers Engine</strong>
              <div className="mt-1 flex items-center gap-space-sm">
                <span className="rounded bg-primary-container px-space-xs py-0.5 font-label-numeric text-[12px] font-bold text-on-primary-container">Captain • {r.captain}x</span>
                <span className="rounded bg-surface-container px-space-xs py-0.5 font-label-numeric text-[12px] font-bold text-on-surface">Vice-Capt • {r.vice_captain}x</span>
              </div>
            </div>
          </div>
          <div className="flex items-start gap-space-sm rounded-lg bg-surface-container-low p-space-xs">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-container font-label-numeric text-[11px] font-bold text-on-surface">3</span>
            <div>
              <strong className="font-semibold text-on-surface">Match teams lock at the start</strong>
              <p className="mt-0.5 text-[13px] text-outline">Series teams can be changed any time and are scored with their current players.</p>
            </div>
          </div>
        </div>
      </div>

      {formats.length > 1 && (
        <Segmented
          value={current.format}
          onChange={setFmt}
          options={formats.map((f) => ({ value: f.format, label: FORMAT_LABEL[f.format] ?? f.format }))}
        />
      )}
      <p className="-mt-space-md font-label-meta text-label-meta text-outline">{current.name}</p>

      <div className="grid grid-cols-1 gap-space-lg md:grid-cols-2">
        {current.sections.map((s) => (
          <div key={s.title} className="flex flex-col gap-space-sm rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
            <h2 className="font-headline-md text-[18px] font-bold text-on-surface">{s.title}</h2>
            <div className="flex flex-col gap-space-xs">
              {s.items.map((item) => {
                const [label, value] = splitPoints(item);
                return (
                  <div key={item} className="flex items-center justify-between gap-space-sm rounded-lg bg-surface-container-low px-space-sm py-space-xs">
                    <span className="font-body-sm text-body-sm text-on-surface-variant">{label}</span>
                    {value && (
                      <span className={`shrink-0 font-label-numeric text-label-numeric font-bold ${value.startsWith("-") ? "text-error" : "text-primary"}`}>
                        {value}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** "Four bonus +4" -> ["Four bonus", "+4"]; "Wicket +30 (not run outs)" keeps its note. */
function splitPoints(item: string): [string, string] {
  const m = item.match(/^(.*?)(?::)?\s([+-]\d+(?:\.\d+)?)(\s.*)?$/);
  return m ? [`${m[1]}${m[3] ?? ""}`, m[2]] : [item, ""];
}
