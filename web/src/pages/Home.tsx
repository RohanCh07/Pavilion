// "Home / Series list" from the Stitch design (web/design/home_series_list).
import { useMemo, useState } from "react";
import { api, type Match, type Series, type Team } from "../api";
import { Icon } from "../components/Icon";
import { btnLow, card, ErrorBox, SearchBox, Skeletons, TeamCircle } from "../components/ui";
import { useMyTeams, useRanks } from "../data";
import { dateRange, pts, startTime, startsIn } from "../format";
import { navigate, useData } from "../hooks";

type Filter = "all" | Series["status"];
const ORDER: Record<Series["status"], number> = { live: 0, upcoming: 1, finished: 2 };

export function Home() {
  const series = useData(() => api.series(), []);
  const matches = useData((fresh) => api.currentMatches(fresh), []);
  const { teams, scores } = useMyTeams();
  const myTeams = teams.data ?? [];
  const rankOf = useRanks(myTeams);
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");

  const counts = useMemo(() => {
    const c = { all: 0, live: 0, upcoming: 0, finished: 0 };
    for (const s of series.data ?? []) {
      c.all++;
      c[s.status]++;
    }
    return c;
  }, [series.data]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (series.data ?? [])
      .filter((s) => filter === "all" || s.status === filter)
      .filter((s) => !q || `${s.name} ${s.short_name}`.toLowerCase().includes(q))
      .sort((a, b) => ORDER[a.status] - ORDER[b.status]);
  }, [series.data, filter, query]);

  const totalPoints = [...scores.values()].reduce((sum, s) => sum + (s?.points ?? 0), 0);

  const pills: { value: Filter; label: string; dot?: boolean }[] = [
    { value: "all", label: `All Series (${counts.all})` },
    { value: "live", label: `Live Now (${counts.live})`, dot: true },
    { value: "upcoming", label: `Upcoming (${counts.upcoming})` },
    { value: "finished", label: `Finished (${counts.finished})` },
  ];

  return (
    <div className="flex w-full flex-col">
      {/* Hero */}
      <div className="relative mb-space-xl w-full overflow-hidden rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm md:p-space-xl">
        <div className="pointer-events-none absolute -top-16 -right-16 h-72 w-72 rounded-full bg-primary-fixed/30 blur-3xl" />
        <div className="pointer-events-none absolute right-1/4 -bottom-24 h-60 w-60 rounded-full bg-secondary-fixed/40 blur-2xl" />
        <div className="relative z-10 flex flex-col justify-between gap-space-lg xl:flex-row xl:items-center">
          <div className="flex max-w-2xl flex-col">
            <div className="mb-space-2xs flex items-center gap-space-xs">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-container px-space-xs py-space-2xs font-label-badge text-label-badge text-primary">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary-container" />
                ACTIVE ROSTER SEASON
              </span>
              <span className="font-label-meta text-label-meta text-outline">· Live from CREX</span>
            </div>
            <h1 className="font-headline-lg text-headline-lg font-bold tracking-tight text-on-surface">Cricket Series</h1>
            <p className="mt-space-2xs font-body-md text-body-md text-on-surface-variant">
              Pick an active tournament or upcoming series to manage your fantasy squad, track live points, and climb the
              leaderboards.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-space-md sm:flex-nowrap">
            <div className="flex items-center gap-space-md rounded-xl bg-surface-container-low p-space-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-container-lowest text-primary shadow-sm">
                <Icon name="workspace_premium" className="text-[24px]" />
              </div>
              <div className="flex min-w-0 flex-col pr-space-xs">
                <div className="flex items-center gap-space-xs">
                  <span className="font-label-numeric text-label-numeric font-bold text-on-surface">{pts(totalPoints)} pts</span>
                  <span className="rounded bg-surface-container-highest px-space-xs py-space-2xs font-label-meta text-label-meta font-bold text-primary">
                    {myTeams.length} {myTeams.length === 1 ? "team" : "teams"}
                  </span>
                </div>
                <span className="truncate font-body-sm text-body-sm text-outline">Across all your fantasy teams</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate("/teams")}
              className="inline-flex items-center justify-center gap-space-xs rounded-lg bg-primary-container px-space-md py-space-sm font-body-md text-body-md font-semibold text-on-primary-container shadow-sm transition-all hover:bg-primary hover:text-on-primary"
            >
              <Icon name="sports_score" className="text-[18px]" />
              <span>My Teams ({myTeams.length})</span>
            </button>
          </div>
        </div>
        <div className="relative z-10 mt-space-lg flex flex-col items-stretch justify-between gap-space-md pt-space-md md:flex-row md:items-center">
          <div className="max-w-md flex-1">
            <SearchBox value={query} onChange={setQuery} placeholder="Filter series by name or nation..." />
          </div>
          <div className="no-scrollbar flex items-center gap-space-xs overflow-x-auto pb-1 md:pb-0">
            {pills.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setFilter(p.value)}
                className={`flex shrink-0 items-center gap-1.5 rounded-lg px-space-md py-space-xs font-body-sm text-body-sm whitespace-nowrap transition-all ${
                  filter === p.value
                    ? "bg-primary-container font-semibold text-on-primary-container"
                    : "bg-surface-container-low font-medium text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {p.dot && <span className="h-2 w-2 animate-pulse rounded-full bg-primary-container" />}
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Series grid */}
      {series.loading && !series.data ? (
        <Skeletons rows={3} height={420} />
      ) : series.error && !series.data ? (
        <ErrorBox message={series.error} onRetry={() => series.reload(true)} />
      ) : shown.length === 0 ? (
        <div className={`${card} p-space-xl text-center font-body-md text-body-md text-outline`}>
          No series match this filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-space-lg md:grid-cols-2 xl:grid-cols-3">
          {shown.map((s) => (
            <SeriesCard
              key={s.id}
              series={s}
              matches={(matches.data ?? []).filter((m) => m.series_id === s.id)}
              teams={myTeams.filter((t) => t.series_id === s.id)}
              rank={myTeams
                .filter((t) => t.series_id === s.id)
                .map(rankOf)
                .filter((r) => r !== null)
                .sort((a, b) => a!.rank - b!.rank)[0] ?? null}
            />
          ))}
        </div>
      )}

      {/* Private leagues banner (placeholder until leagues exist) */}
      <div className="mt-space-2xl flex flex-col items-center justify-between gap-space-lg rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm md:flex-row">
        <div className="flex items-center gap-space-md">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-container/20 text-primary">
            <Icon name="speed" className="text-[28px]" />
          </div>
          <div>
            <h3 className="font-headline-md text-headline-md font-bold text-on-surface">Looking for custom private leagues?</h3>
            <p className="font-body-md text-body-md text-outline">
              Private leagues with your friends are coming soon. For now, every series has one open leaderboard.
            </p>
          </div>
        </div>
        <button
          type="button"
          disabled
          className="w-full rounded-lg bg-surface-container px-space-lg py-space-sm font-body-md text-body-md font-semibold whitespace-nowrap text-outline md:w-auto"
        >
          Coming soon
        </button>
      </div>
    </div>
  );
}

function SeriesCard({
  series: s,
  matches,
  teams,
  rank,
}: {
  series: Series;
  matches: Match[];
  teams: Team[];
  rank: { rank: number; of: number } | null;
}) {
  const live = matches.find((m) => m.status === "LIVE");
  const next = matches.filter((m) => m.status === "NS").sort((a, b) => a.start.localeCompare(b.start))[0];
  const last = matches.filter((m) => m.status === "FT").sort((a, b) => b.start.localeCompare(a.start))[0];
  const tour = /tour|vs|in /i.test(s.name);
  const label = s.short_name && s.short_name.length <= 24 ? s.short_name : s.name.split(" ").slice(0, 3).join(" ");
  const open = () => navigate(`/series/${s.id}`);

  return (
    <div className="group flex flex-col justify-between rounded-2xl bg-surface-container-lowest p-space-lg shadow-sm transition-all hover:shadow-md">
      <div>
        {/* Banner (the design's image slot; no artwork yet, so its no-image variants) */}
        <button type="button" onClick={open} className="relative mb-space-md block h-36 w-full overflow-hidden rounded-xl text-left">
          {s.status === "live" ? (
            <div className="relative flex h-full w-full items-center justify-center overflow-hidden bg-[#0b1c30]">
              <div className="absolute -right-10 -bottom-10 h-40 w-40 rounded-full bg-primary-container/40 blur-2xl" />
              <div className="absolute -top-12 -left-12 h-32 w-32 rounded-full bg-primary-fixed/20 blur-2xl" />
              <div className="relative flex flex-col items-center text-primary-fixed">
                <Icon name="stadium" className="text-[40px]" />
              </div>
            </div>
          ) : s.status === "finished" ? (
            <div className="flex h-full w-full flex-col items-center justify-center bg-surface-container-low">
              <Icon name="emoji_events" className="text-[36px] text-outline" />
              <span className="mt-1 font-label-meta text-label-meta font-bold tracking-widest text-outline uppercase">Concluded</span>
            </div>
          ) : (
            <div className="relative flex h-full w-full items-center justify-center overflow-hidden bg-surface-container">
              {tour ? (
                <div className="absolute -right-8 -bottom-8 h-28 w-28 rounded-full bg-primary-fixed/40 blur-xl" />
              ) : (
                <div className="absolute inset-0 bg-gradient-to-tr from-secondary-container to-surface-container-high opacity-50" />
              )}
              <div className="relative flex flex-col items-center">
                <Icon name={tour ? "flight_takeoff" : "sports_cricket"} className={`text-[36px] ${tour ? "text-primary" : "text-secondary"}`} />
                <span className={`mt-1 font-label-meta text-label-meta font-bold tracking-widest uppercase ${tour ? "text-primary" : "text-secondary"}`}>
                  {tour ? "Bilateral Tour" : "Tournament"}
                </span>
              </div>
            </div>
          )}
          <div className="absolute top-space-sm left-space-sm">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full bg-surface-container-lowest/90 px-space-xs py-space-2xs font-label-badge text-label-badge shadow-sm backdrop-blur-md ${
                s.status === "live" ? "text-primary" : s.status === "upcoming" && next ? "text-on-surface" : "text-outline"
              }`}
            >
              {s.status === "live" && <span className="h-1.5 w-1.5 animate-ping rounded-full bg-primary-container" />}
              {s.status === "upcoming" && next && <span className="h-1.5 w-1.5 rounded-full bg-tertiary-container" />}
              {s.status === "live"
                ? tour
                  ? "SERIES LIVE"
                  : "LIVE TOURNAMENT"
                : s.status === "finished"
                  ? "COMPLETED"
                  : next
                    ? startsIn(next.start).toUpperCase()
                    : "UPCOMING"}
            </span>
          </div>
          <div
            className={`absolute right-space-sm bottom-space-xs left-space-sm flex items-center justify-between ${
              s.status === "live" ? "text-on-primary" : "text-on-surface"
            }`}
          >
            <span className="truncate font-label-numeric text-label-numeric font-bold tracking-wider">{label}</span>
            {matches.length > 0 && (
              <span className={`shrink-0 font-label-meta text-label-meta ${s.status === "live" ? "text-surface-container-high" : "text-outline"}`}>
                {matches.length} {matches.length === 1 ? "match" : "matches"} listed
              </span>
            )}
          </div>
        </button>

        <div className="mb-space-2xs flex items-start justify-between gap-space-xs">
          <h2 className="font-headline-md text-headline-md font-bold text-on-surface transition-colors group-hover:text-primary">{s.name}</h2>
        </div>
        <p className="mb-space-md font-body-sm text-body-sm text-outline">{dateRange(s.start, s.end)}</p>

        {/* Status box */}
        <div className="mb-space-md rounded-xl bg-surface-container-low p-space-sm">
          {live ? (
            <>
              <div className="mb-space-2xs flex items-center justify-between text-on-surface-variant">
                <span className="font-label-meta text-label-meta font-bold tracking-wider text-primary uppercase">In-Play Today</span>
                <span className="font-label-numeric text-label-numeric font-semibold text-on-surface">Live</span>
              </div>
              <ScoreRow match={live} />
            </>
          ) : next ? (
            <>
              <div className="mb-space-2xs flex items-center justify-between text-on-surface-variant">
                <span className="font-label-meta text-label-meta font-bold tracking-wider text-outline uppercase">Next Match</span>
                <span className="font-label-numeric text-label-numeric text-outline">{startTime(next.start)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-body-sm text-body-sm font-bold text-on-surface">
                  {next.home.name} vs {next.away.name}
                </span>
              </div>
              <p className="mt-1 flex items-center gap-1 font-body-sm text-body-sm font-semibold text-primary-container">
                <Icon name="check_circle" className="text-[16px]" />
                Squads open. Build your team now.
              </p>
            </>
          ) : last ? (
            <>
              <div className="mb-space-2xs flex items-center justify-between text-on-surface-variant">
                <span className="font-label-meta text-label-meta font-bold tracking-wider text-outline uppercase">Latest Result</span>
              </div>
              <ScoreRow match={last} />
            </>
          ) : (
            <>
              <div className="mb-space-2xs flex items-center justify-between text-on-surface-variant">
                <span className="font-label-meta text-label-meta font-bold tracking-wider text-outline uppercase">Fixtures</span>
              </div>
              <p className="font-body-sm text-body-sm text-on-surface-variant">Open the series to see its full schedule.</p>
            </>
          )}
        </div>

        <div className="flex items-center justify-between px-space-xs pb-space-sm font-label-numeric text-label-numeric">
          <div className="flex items-center gap-1.5 text-on-surface-variant">
            <Icon name="group" className={`text-[16px] ${teams.length ? "text-primary" : "text-outline"}`} />
            <span>
              {teams.length} {teams.length === 1 ? "Squad" : "Squads"} Active
            </span>
          </div>
          <span
            className={`rounded px-space-xs py-space-2xs font-bold ${
              rank ? "bg-surface-container text-primary" : "bg-surface-container-high font-medium text-on-surface"
            }`}
          >
            {rank ? `Rank #${rank.rank} / ${rank.of}` : "Rank —"}
          </span>
        </div>
      </div>
      <div className="mt-space-xs flex items-center gap-space-sm pt-space-sm">
        <button
          type="button"
          onClick={open}
          className="flex-1 rounded-lg bg-primary-container py-space-sm text-center font-body-sm text-body-sm font-semibold text-on-primary-container transition-all hover:bg-primary hover:text-on-primary md:py-space-xs"
        >
          {s.status === "finished" ? "View Standings" : "View Series"}
        </button>
        {s.status !== "finished" && (
          <button
            type="button"
            onClick={() => navigate(teams.length ? `/series/${s.id}?tab=teams` : `/series/${s.id}/build`)}
            className={`${btnLow} py-space-sm md:py-space-xs`}
          >
            {teams.length ? `My Teams (${teams.length})` : "Create Team"}
          </button>
        )}
      </div>
    </div>
  );
}

function ScoreRow({ match }: { match: Match }) {
  return (
    <>
      <div className="flex items-center justify-between gap-space-xs">
        <div className="flex min-w-0 items-center gap-space-xs">
          <TeamCircle name={match.home.name} />
          <span className="truncate font-body-sm text-body-sm font-bold text-on-surface">{match.home.score || "—"}</span>
        </div>
        <span className="font-label-meta text-label-meta font-semibold text-outline">vs</span>
        <div className="flex min-w-0 items-center gap-space-xs">
          <span className="truncate font-body-sm text-body-sm font-bold text-on-surface">{match.away.score || "—"}</span>
          <TeamCircle name={match.away.name} />
        </div>
      </div>
      <p className="mt-1 truncate font-body-sm text-body-sm text-outline">
        {match.result || `${match.home.name} vs ${match.away.name}`}
      </p>
    </>
  );
}
