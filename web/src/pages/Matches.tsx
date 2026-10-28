// Match Center: live, upcoming and recent matches across all series, using the design's match cards.
import { useMemo, useState } from "react";
import { api, type Match } from "../api";
import { MatchCard } from "../components/MatchCard";
import { EmptyPanel, ErrorBox, FilterChips, Skeletons } from "../components/ui";
import { useMyTeams } from "../data";
import { useData } from "../hooks";

type Filter = "all" | "LIVE" | "NS" | "FT";

export function Matches() {
  const matches = useData((fresh) => api.currentMatches(fresh), []);
  const { teams, scores } = useMyTeams();
  const [filter, setFilter] = useState<Filter>("all");
  const all = matches.data ?? [];
  const rank = { LIVE: 0, NS: 1, FT: 2 } as const;
  const shown = useMemo(
    () =>
      [...all]
        .filter((m) => filter === "all" || m.status === filter)
        .sort((a: Match, b: Match) =>
          a.status !== b.status ? rank[a.status] - rank[b.status] : a.status === "FT" ? b.start.localeCompare(a.start) : a.start.localeCompare(b.start),
        ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [all, filter],
  );
  const count = (s: Match["status"]) => all.filter((m) => m.status === s).length;

  return (
    <div className="flex w-full flex-col gap-space-lg">
      <div className="flex flex-col">
        <div className="mb-space-2xs flex items-center gap-space-xs text-outline">
          <span className="font-label-meta text-label-meta font-semibold tracking-wider uppercase">Match Center</span>
          <span className="font-label-meta text-label-meta">•</span>
          <span className="font-label-numeric text-label-numeric font-medium text-primary">Live from CREX</span>
        </div>
        <h1 className="font-headline-xl-mobile text-headline-xl-mobile tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">Matches</h1>
        <p className="mt-space-2xs max-w-2xl font-body-md text-body-md text-on-surface-variant">
          Every live, upcoming and recent match across the series. Build a match team before it starts.
        </p>
      </div>
      <FilterChips
        value={filter}
        onChange={setFilter}
        options={[
          { value: "all", label: `ALL (${all.length})` },
          { value: "LIVE", label: `LIVE (${count("LIVE")})` },
          { value: "NS", label: `UPCOMING (${count("NS")})` },
          { value: "FT", label: `COMPLETED (${count("FT")})` },
        ]}
      />
      {matches.loading && !matches.data ? (
        <Skeletons rows={3} height={230} />
      ) : matches.error && !matches.data ? (
        <ErrorBox message={matches.error} onRetry={() => matches.reload(true)} />
      ) : shown.length === 0 ? (
        <EmptyPanel icon="event_busy" title="No matches here" text="Try another filter." />
      ) : (
        <div className="grid grid-cols-1 gap-space-lg xl:grid-cols-2">
          {shown.map((m) => {
            const myTeam = (teams.data ?? []).find((t) => t.match_id === m.id);
            const s = myTeam ? scores.get(myTeam.id) : undefined;
            const ms = s?.matches.find((x) => x.match.id === m.id);
            return (
              <div key={m.id} className="flex flex-col gap-space-2xs">
                <span className="px-space-xs font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase">{m.series_name}</span>
                <MatchCard match={m} myTeam={myTeam} myScore={s && ms ? { ...s, points: ms.points, players: ms.players } : null} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
