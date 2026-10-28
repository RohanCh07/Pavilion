// "My Teams" from the Stitch design (web/design/my_teams_management).
import { useMemo, useState } from "react";
import { api, type Match, type Team } from "../api";
import { Icon } from "../components/Icon";
import { teamState, TeamCard } from "../components/TeamCard";
import { btnPrimary, EmptyPanel, ErrorBox, Segmented, Skeletons } from "../components/ui";
import { useMyTeams, useRanks } from "../data";
import { dateRange, pts } from "../format";
import { navigate, useData } from "../hooks";

type Filter = "all" | "live" | "upcoming" | "finished";

export function MyTeams() {
  const { teams, scores } = useMyTeams();
  const list = teams.data ?? [];
  const rankOf = useRanks(list);
  const series = useData(() => api.series(), []);
  const current = useData((fresh) => api.currentMatches(fresh), []);
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [sortByPoints, setSortByPoints] = useState(false);

  // Coarse status per team from the match centre, for the tab counts.
  const matchesBySeries = useMemo(() => {
    const out = new Map<number, Match[]>();
    for (const m of current.data ?? []) out.set(m.series_id, [...(out.get(m.series_id) ?? []), m]);
    return out;
  }, [current.data]);
  const seriesStatus = new Map((series.data ?? []).map((s) => [s.id, s.status]));
  const status = (t: Team): Filter => {
    const inSeries = matchesBySeries.get(t.series_id) ?? [];
    if (t.match_id !== null) {
      const s = teamState(t, inSeries);
      return s === "series" ? "upcoming" : s;
    }
    if (inSeries.some((m) => m.status === "LIVE")) return "live";
    return seriesStatus.get(t.series_id) === "finished" ? "finished" : "upcoming";
  };
  const counts = { all: list.length, live: 0, upcoming: 0, finished: 0 };
  for (const t of list) counts[status(t)]++;

  const shown = list
    .filter((t) => filter === "all" || status(t) === filter)
    .filter((t) => !query.trim() || `${t.name} ${t.series_name}`.toLowerCase().includes(query.trim().toLowerCase()))
    .sort((a, b) =>
      sortByPoints ? (scores.get(b.id)?.points ?? 0) - (scores.get(a.id)?.points ?? 0) : b.id - a.id,
    );

  const total = [...scores.values()].reduce((sum, s) => sum + (s?.points ?? 0), 0);
  const entered = new Set(list.map((t) => t.series_id));
  const open = (series.data ?? []).filter((s) => s.status !== "finished" && !entered.has(s.id)).slice(0, 3);

  return (
    <div className="flex w-full flex-col">
      <div className="mb-space-xl flex flex-col justify-between gap-space-lg md:flex-row md:items-end">
        <div className="flex flex-col">
          <div className="mb-space-2xs flex items-center gap-space-xs text-outline">
            <span className="font-label-meta text-label-meta font-semibold tracking-wider uppercase">Pavilion Squad Vault</span>
            <span className="font-label-meta text-label-meta">•</span>
            <span className="font-label-numeric text-label-numeric font-medium text-primary">Synced live</span>
          </div>
          <h1 className="font-headline-xl-mobile text-headline-xl-mobile tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">
            My Fantasy Teams
          </h1>
          <p className="mt-space-2xs max-w-2xl font-body-md text-body-md text-on-surface-variant">
            Manage your series and match squads, track live points, and refine rosters before the match locks them.
          </p>
        </div>
        <div className="flex items-center gap-space-sm">
          <div className="hidden items-center gap-space-md rounded-xl bg-surface-container-lowest px-space-md py-space-xs shadow-sm xl:flex">
            <div className="flex flex-col">
              <span className="font-label-meta text-label-meta text-outline uppercase">Total Points</span>
              <span className="font-label-numeric text-label-numeric font-bold text-on-surface">{pts(total)}</span>
            </div>
            <div className="h-8 w-px bg-surface-container-high" />
            <div className="flex flex-col">
              <span className="font-label-meta text-label-meta text-outline uppercase">Teams</span>
              <span className="font-label-numeric text-label-numeric font-bold text-primary">{list.length}</span>
            </div>
          </div>
          <button type="button" onClick={() => navigate("/")} className={`${btnPrimary} w-full px-space-lg py-space-sm md:w-auto`}>
            <Icon name="add_circle" className="text-[20px]" />
            <span>Create New Team</span>
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-space-md pb-space-lg">
        <Segmented
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: "All Teams", count: counts.all },
            { value: "live", label: "Live Matches", count: counts.live, dot: true },
            { value: "upcoming", label: "Upcoming", count: counts.upcoming },
            { value: "finished", label: "Finished", count: counts.finished },
          ]}
        />
        <div className="flex w-full items-center gap-space-xs sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Icon name="search" className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-[18px] text-outline" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by team or series..."
              className="w-full rounded-lg border-0 bg-surface-container-lowest py-space-xs pr-3 pl-9 font-body-sm text-body-sm text-on-surface shadow-sm focus:ring-2 focus:ring-primary-container focus:outline-none"
              style={{ minHeight: 36 }}
            />
          </div>
          <button
            type="button"
            onClick={() => setSortByPoints(!sortByPoints)}
            aria-label={sortByPoints ? "Sort by newest" : "Sort by points"}
            title={sortByPoints ? "Sorted by points" : "Sorted by newest"}
            className={`rounded-lg p-space-xs shadow-sm ${sortByPoints ? "bg-primary-container text-on-primary-container" : "bg-surface-container-lowest text-on-surface-variant hover:text-on-surface"}`}
          >
            <Icon name="sort" className="text-[20px]" />
          </button>
        </div>
      </div>

      <div className="flex w-full flex-col gap-space-lg">
        {teams.loading && !teams.data ? (
          <Skeletons rows={2} height={300} />
        ) : teams.error && !teams.data ? (
          <ErrorBox message={teams.error} onRetry={() => teams.reload(true)} />
        ) : shown.length === 0 ? (
          <EmptyPanel
            icon="emoji_events"
            title={list.length ? "No teams in this view" : "No teams yet"}
            text={list.length ? "Try another tab or clear the search." : "Pick a series, then build a team for the whole series or a single match."}
            action={
              !list.length && (
                <button type="button" onClick={() => navigate("/")} className={`${btnPrimary} px-space-xl py-space-sm`}>
                  <Icon name="add" className="text-[18px]" />
                  <span>Create Team</span>
                </button>
              )
            }
          />
        ) : (
          shown.map((t) => <TeamCard key={t.id} team={t} score={scores.get(t.id)} rank={rankOf(t)} onDeleted={() => teams.reload(true)} />)
        )}
      </div>

      {open.length > 0 && (
        <div className="mt-space-2xl border-t border-surface-container-high pt-space-xl">
          <div className="mb-space-lg flex flex-col justify-between gap-space-md md:flex-row md:items-center">
            <div>
              <span className="font-label-meta text-label-meta font-bold tracking-wider text-outline uppercase">Unentered Tournaments</span>
              <h3 className="font-headline-md text-headline-md font-bold text-on-surface">Available Fantasy Leagues</h3>
            </div>
            <span className="font-label-numeric text-label-numeric text-outline">Series you haven't entered</span>
          </div>
          <div className="flex flex-col gap-space-md">
            {open.map((s) => (
              <div key={s.id} className="flex w-full flex-col items-center justify-between gap-space-lg rounded-2xl bg-surface-container-low p-space-lg md:flex-row lg:p-space-xl">
                <div className="flex w-full items-center gap-space-lg">
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-surface-container-highest text-primary">
                    <Icon name="sports_cricket" className="text-[36px]" />
                  </div>
                  <div className="flex min-w-0 flex-col">
                    <div className="flex flex-wrap items-center gap-space-xs">
                      <h4 className="font-headline-md text-headline-md font-bold text-on-surface">{s.name}</h4>
                      <span className="rounded bg-surface-container px-space-xs py-space-2xs font-label-badge text-label-badge font-bold text-on-surface-variant">
                        {s.status === "live" ? "LIVE SERIES" : "UPCOMING"}
                      </span>
                    </div>
                    <p className="mt-1 font-body-md text-body-md text-on-surface-variant">No squads registered yet. Build your lineup and climb the leaderboard.</p>
                    <div className="mt-space-xs flex items-center gap-space-md font-label-meta text-label-meta text-outline">
                      <span className="flex items-center gap-1">
                        <Icon name="event" className="text-[14px]" /> {dateRange(s.start, s.end)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex w-full shrink-0 items-center justify-end gap-space-sm md:w-auto">
                  <button
                    type="button"
                    onClick={() => navigate(`/series/${s.id}`)}
                    className="rounded-lg bg-surface-container-lowest px-space-lg py-space-sm font-body-sm text-body-sm font-semibold text-on-surface shadow-sm transition-colors hover:bg-surface-container-high"
                  >
                    View Series
                  </button>
                  <button type="button" onClick={() => navigate(`/series/${s.id}/build`)} className={`${btnPrimary} px-space-xl py-space-sm`}>
                    <Icon name="add" className="text-[18px]" />
                    <span>Create Team</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
