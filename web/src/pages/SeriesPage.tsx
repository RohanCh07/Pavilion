// "Series page" from the Stitch design (web/design/series_page_matches).
import { useMemo, useState } from "react";
import { api, peek, type Match, type Series } from "../api";
import { Icon } from "../components/Icon";
import { MatchCard } from "../components/MatchCard";
import { TeamCard } from "../components/TeamCard";
import { Breadcrumb, btnPrimary, card, EmptyPanel, ErrorBox, FilterChips, LivePill, MetricTile, Segmented, Skeletons } from "../components/ui";
import { useMyTeams, useRanks } from "../data";
import { dateRange, pts } from "../format";
import { navigate, useData } from "../hooks";
import { useUser } from "../user";

type Tab = "matches" | "teams" | "leaderboard";
type Filter = "all" | "LIVE" | "NS" | "FT";

function order(matches: Match[]): Match[] {
  const rank = { LIVE: 0, NS: 1, FT: 2 } as const;
  return [...matches].sort((a, b) => {
    if (a.status !== b.status) return rank[a.status] - rank[b.status];
    const diff = a.start.localeCompare(b.start);
    return a.status === "FT" ? -diff : diff;
  });
}

export function SeriesPage({ seriesId, tab }: { seriesId: number; tab: Tab }) {
  const user = useUser();
  const seriesList = useData(() => api.series(), []);
  const series: Series | undefined =
    (seriesList.data ?? peek<Series[]>("/api/series"))?.find((s) => s.id === seriesId);
  const matches = useData((fresh) => api.matches(seriesId, fresh), [seriesId]);
  const board = useData((fresh) => api.leaderboard(seriesId, fresh), [seriesId]);
  const rules = useData(() => api.rules(), []);
  const { teams, scores } = useMyTeams();
  const mine = (teams.data ?? []).filter((t) => t.series_id === seriesId);
  const rankOf = useRanks(mine);
  const [filter, setFilter] = useState<Filter>("all");

  const all = matches.data ?? [];
  const name = series?.name ?? all[0]?.series_name ?? "Series";
  const done = all.filter((m) => m.status === "FT").length;
  const live = all.some((m) => m.status === "LIVE") || series?.status === "live";
  const shown = useMemo(() => order(all).filter((m) => filter === "all" || m.status === filter), [all, filter]);
  const setTab = (t: Tab) => navigate(`/series/${seriesId}${t === "matches" ? "" : `?tab=${t}`}`, true);

  const seriesTeams = mine.filter((t) => t.match_id === null);
  const best = seriesTeams
    .map((t) => ({ t, points: scores.get(t.id)?.points ?? 0, rank: rankOf(t) }))
    .sort((a, b) => b.points - a.points)[0];
  const count = (s: Match["status"]) => all.filter((m) => m.status === s).length;

  return (
    <div className="flex w-full flex-col gap-space-xl">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-xl bg-surface-container-lowest p-space-lg shadow-sm lg:p-space-2xl">
        <div className="pointer-events-none absolute -top-24 -right-24 h-96 w-96 rounded-full bg-primary-container/10 blur-3xl" />
        <div className="pointer-events-none absolute right-0 bottom-0 hidden pr-space-lg pb-space-xs opacity-5 md:block">
          <span className="font-label-numeric text-[120px] leading-none font-black text-on-surface select-none">CRK</span>
        </div>
        <div className="relative z-10 flex flex-col gap-space-lg">
          <div className="flex flex-wrap items-center justify-between gap-space-sm">
            <Breadcrumb backTo="/" label="Series" current={name} />
            <div className="flex items-center gap-space-xs">
              {live ? (
                <LivePill label="Live now" soft />
              ) : (
                <span className="rounded-full bg-surface-container px-space-sm py-space-2xs font-label-badge text-label-badge tracking-wider text-secondary uppercase">
                  {series?.status === "finished" ? "Completed" : "Upcoming"}
                </span>
              )}
              {all.length > 0 && (
                <span className="rounded-full bg-surface-container px-space-sm py-space-2xs font-label-numeric text-label-numeric text-secondary">
                  Match {Math.min(all.length, done + (live ? 1 : 0)) || 1} of {all.length}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col justify-between gap-space-lg xl:flex-row xl:items-end">
            <div className="flex max-w-3xl flex-col gap-space-xs">
              <div className="flex flex-wrap items-center gap-space-sm">
                <h1 className="font-headline-xl-mobile text-headline-xl-mobile font-bold tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">
                  {name}
                </h1>
                <Icon name="verified" className="text-[26px] text-primary" title="Official series" />
              </div>
              <div className="flex flex-wrap items-center gap-x-space-md gap-y-space-xs font-body-sm text-body-sm text-on-surface-variant">
                {series?.start && (
                  <>
                    <div className="flex items-center gap-space-2xs">
                      <Icon name="calendar_today" className="text-[17px] text-outline" />
                      <span className="font-medium">{dateRange(series.start, series.end)}</span>
                    </div>
                    <span className="text-outline-variant">•</span>
                  </>
                )}
                <div className="flex items-center gap-space-2xs">
                  <Icon name="sports_cricket" className="text-[17px] text-outline" />
                  <span>{all.length} Matches</span>
                </div>
                <span className="text-outline-variant">•</span>
                <div className="flex items-center gap-space-2xs">
                  <Icon name="toll" className="text-[17px] text-outline" />
                  <span className="font-label-numeric text-label-numeric font-semibold text-primary">Free to play</span>
                </div>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-space-sm sm:flex-nowrap">
              <button
                type="button"
                onClick={() => navigate("/rules")}
                className="inline-flex flex-1 items-center justify-center gap-space-xs rounded-lg bg-surface-container-low px-space-lg py-space-sm font-body-sm text-body-sm font-semibold text-on-surface transition-all hover:bg-surface-container active:scale-[0.98] sm:flex-none"
              >
                <Icon name="gavel" className="text-[18px]" />
                <span>Rules &amp; Points</span>
              </button>
              <button
                type="button"
                onClick={() => navigate(`/pools/new?series=${seriesId}`)}
                className="inline-flex flex-1 items-center justify-center gap-space-xs rounded-lg bg-surface-container-low px-space-lg py-space-sm font-body-sm text-body-sm font-semibold text-on-surface transition-all hover:bg-surface-container active:scale-[0.98] sm:flex-none"
              >
                <Icon name="groups" className="text-[18px]" />
                <span>Create Pool</span>
              </button>
              <button
                type="button"
                onClick={() => navigate(`/series/${seriesId}/build`)}
                className={`${btnPrimary} w-full px-space-lg py-space-sm sm:w-auto sm:flex-none`}
              >
                <Icon name="add_circle" className="text-[18px]" />
                <span>Create Series Team</span>
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-space-sm pt-space-md sm:grid-cols-4">
            <MetricTile label="Total Fantasy Entries" value={board.data ? board.data.length.toLocaleString() : "…"} />
            <MetricTile
              label="Your Total Points"
              accent
              value={best ? pts(best.points) : "—"}
              sub={best?.rank ? `(Rank #${best.rank.rank})` : undefined}
            />
            <MetricTile label="Prize Pool" value="—" sub="(coming soon)" />
            <MetricTile
              label="Matches Concluded"
              value={
                <>
                  {done} <span className="font-normal text-outline">/ {all.length}</span>
                </>
              }
            />
          </div>
        </div>
      </section>

      {/* Tabs + filters */}
      <div className="flex flex-col justify-between gap-space-md sm:flex-row sm:items-center">
        <Segmented
          value={tab}
          onChange={setTab}
          options={[
            { value: "matches", label: "Matches", count: all.length },
            { value: "teams", label: "My Teams", count: mine.length },
            { value: "leaderboard", label: "Leaderboard", count: board.data?.length },
          ]}
        />
        {tab === "matches" && (
          <FilterChips
            value={filter}
            onChange={setFilter}
            options={[
              { value: "all", label: "ALL" },
              { value: "LIVE", label: `LIVE (${count("LIVE")})` },
              { value: "NS", label: `UPCOMING (${count("NS")})` },
              { value: "FT", label: `COMPLETED (${count("FT")})` },
            ]}
          />
        )}
      </div>

      <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
        <div className="flex flex-col gap-space-lg lg:col-span-8">
          {tab === "matches" &&
            (matches.loading && !matches.data ? (
              <Skeletons rows={3} height={230} />
            ) : matches.error && !matches.data ? (
              <ErrorBox message={matches.error} onRetry={() => matches.reload(true)} />
            ) : shown.length === 0 ? (
              <EmptyPanel icon="event_busy" title="No matches here" text="Try another filter." />
            ) : (
              shown.map((m) => {
                const myTeam = mine.find((t) => t.match_id === m.id);
                const myScore = myTeam ? scores.get(myTeam.id) : undefined;
                const matchScore = myScore?.matches.find((x) => x.match.id === m.id);
                return (
                  <MatchCard
                    key={m.id}
                    match={m}
                    myTeam={myTeam}
                    myScore={
                      myScore && matchScore
                        ? { ...myScore, points: matchScore.points, players: matchScore.players.map((p) => ({ ...p })) }
                        : null
                    }
                  />
                );
              })
            ))}

          {tab === "teams" &&
            (teams.loading && !teams.data ? (
              <Skeletons rows={2} height={260} />
            ) : mine.length === 0 ? (
              <EmptyPanel
                title="No teams for this series yet"
                text="Build one for the whole series, or for a single match from the Matches tab."
                action={
                  <button type="button" className={`${btnPrimary} px-space-xl py-space-sm`} onClick={() => navigate(`/series/${seriesId}/build`)}>
                    <Icon name="add" className="text-[18px]" />
                    <span>Create Team</span>
                  </button>
                }
              />
            ) : (
              mine.map((t) => (
                <TeamCard key={t.id} team={t} score={scores.get(t.id)} rank={rankOf(t)} onDeleted={() => teams.reload(true)} />
              ))
            ))}

          {tab === "leaderboard" && <LeaderboardList rows={board.data} loading={board.loading} user={user} />}
        </div>

        {/* Side panel */}
        <aside className="flex flex-col gap-space-lg lg:col-span-4">
          <div className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
            <div className="flex items-center justify-between pb-space-2xs">
              <div className="flex items-center gap-space-xs">
                <Icon name="emoji_events" className="text-[20px] text-primary" />
                <h2 className="font-headline-md text-[18px] font-bold text-on-surface">Series Leaderboard</h2>
              </div>
              <button type="button" onClick={() => setTab("leaderboard")} className="font-label-meta text-label-meta font-semibold text-primary hover:underline">
                View All ({board.data?.length ?? 0})
              </button>
            </div>
            <p className="-mt-space-xs font-body-sm text-body-sm text-on-surface-variant">Series teams ranked by total fantasy points.</p>
            <LeaderboardRows rows={(board.data ?? []).slice(0, 3)} user={user} />
            {board.data && board.data.length > 0 && best?.rank && best.rank.rank > 1 && (
              <div className="flex items-center justify-between pt-space-xs font-label-numeric text-label-meta text-outline">
                <span>Points difference to #1:</span>
                <span className="font-semibold text-on-surface">{pts(board.data[0].points - best.points)} pts needed</span>
              </div>
            )}
            {board.data && board.data.length === 0 && (
              <p className="font-body-sm text-body-sm text-outline">No series teams yet. Be the first.</p>
            )}
          </div>

          <div className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
            <div className="flex items-center gap-space-xs">
              <Icon name="fact_check" className="text-[20px] text-outline" />
              <h2 className="font-headline-md text-[18px] font-bold text-on-surface">Series Fantasy Rules</h2>
            </div>
            <div className="flex flex-col gap-space-sm font-body-sm text-body-sm text-on-surface-variant">
              <RuleRow n={1} title={`Up to ${rules.data?.team_max_players ?? 11} Players per Roster:`} text="Pick from both squads of the series, or of one match." />
              <RuleRow n={2} title="Points from real stats:" text="Runs, wickets, catches and more, scored from the live scorecard." />
              <div className="flex items-start gap-space-sm rounded-lg bg-surface-container-low p-space-xs">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-container font-label-numeric text-[11px] font-bold text-on-surface">3</span>
                <div>
                  <strong className="font-semibold text-on-surface">Multipliers Engine:</strong>
                  <div className="mt-1 flex items-center gap-space-sm">
                    <span className="inline-flex items-center gap-space-2xs rounded bg-primary-container px-space-xs py-0.5 font-label-numeric text-[12px] font-bold text-on-primary-container">
                      Captain • {rules.data?.captain ?? 2}x
                    </span>
                    <span className="inline-flex items-center gap-space-2xs rounded bg-surface-container px-space-xs py-0.5 font-label-numeric text-[12px] font-bold text-on-surface">
                      Vice-Capt • {rules.data?.vice_captain ?? 1.5}x
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate("/rules")}
              className="w-full rounded-lg bg-surface-container py-space-sm font-body-sm text-body-sm font-semibold text-on-surface transition-colors hover:bg-surface-container-high"
            >
              View Complete Scoring Rubric
            </button>
          </div>

          <div className="flex flex-col gap-space-sm rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-xs">
                <Icon name="cloud" className="text-[20px] text-outline" />
                <span className="font-body-sm text-body-sm font-bold text-on-surface">Venue Ground Conditions</span>
              </div>
              <span className="font-label-meta text-label-meta text-outline">Coming soon</span>
            </div>
            <div className="relative flex h-36 w-full items-center justify-center overflow-hidden rounded-lg bg-surface-container">
              <svg className="h-full w-full text-primary/10" fill="none" viewBox="0 0 300 140" xmlns="http://www.w3.org/2000/svg">
                <ellipse cx="150" cy="70" rx="140" ry="60" stroke="currentColor" strokeWidth="2" />
                <ellipse cx="150" cy="70" rx="90" ry="38" stroke="currentColor" strokeDasharray="4 4" strokeWidth="1.5" />
                <rect fill="currentColor" height="50" rx="2" width="30" x="135" y="45" />
              </svg>
              <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-transparent to-transparent" />
              <div className="absolute right-3 bottom-2 left-3 flex items-center justify-between">
                <span className="font-label-meta text-label-meta font-semibold text-on-surface">Pitch report: —</span>
                <span className="font-label-meta text-label-meta font-semibold text-primary">Pace — • Spin —</span>
              </div>
            </div>
            <div className="flex items-center justify-between pt-space-2xs font-label-meta text-label-meta text-outline">
              <span>Venue and weather data aren't available yet.</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function RuleRow({ n, title, text }: { n: number; title: string; text: string }) {
  return (
    <div className="flex items-start gap-space-sm rounded-lg bg-surface-container-low p-space-xs">
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-container font-label-numeric text-[11px] font-bold text-on-surface">
        {n}
      </span>
      <div>
        <strong className="font-semibold text-on-surface">{title}</strong>
        <p className="mt-0.5 font-body-sm text-[13px] text-outline">{text}</p>
      </div>
    </div>
  );
}

type Row = { rank: number; team_id: number; team_name: string; owner: string; points: number; matches_scored: number };

const MEDAL = ["bg-tertiary-fixed text-on-tertiary-fixed", "bg-secondary-fixed text-on-secondary-fixed", "bg-surface-container-high text-on-surface"];

export function LeaderboardRows({ rows, user }: { rows: Row[]; user: string }) {
  return (
    <div className="flex flex-col gap-space-xs">
      {rows.map((r) => {
        const you = r.owner === user;
        return (
          <button
            key={r.team_id}
            type="button"
            onClick={() => navigate(`/teams/${r.team_id}`)}
            className={`flex items-center justify-between rounded-lg p-space-sm text-left transition-colors ${
              you ? "bg-primary-container/15" : "bg-surface-container-low hover:bg-surface-container"
            }`}
          >
            <div className="flex min-w-0 items-center gap-space-sm">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-label-numeric text-[12px] font-bold ${
                  you ? "bg-primary-container text-on-primary-container" : (MEDAL[r.rank - 1] ?? "bg-surface-container text-on-surface")
                }`}
              >
                {r.rank}
              </span>
              <div className="flex min-w-0 flex-col">
                <div className="flex items-center gap-space-2xs">
                  <span className={`truncate font-body-sm text-body-sm font-bold ${you ? "text-primary" : "text-on-surface"}`}>{r.team_name}</span>
                  {r.rank === 1 && !you && <Icon name="star" className="text-[14px] text-tertiary" />}
                  {you && <span className="rounded bg-primary px-space-2xs py-0.5 font-label-badge text-[9px] font-bold text-on-primary uppercase">You</span>}
                </div>
                <span className="truncate font-label-meta text-label-meta text-outline">Manager: {r.owner}</span>
              </div>
            </div>
            <div className="shrink-0 text-right">
              <span className={`font-label-numeric text-label-numeric font-bold ${you ? "text-primary" : "text-on-surface"}`}>{pts(r.points)}</span>
              <span className={`block font-label-meta text-[10px] ${you ? "text-primary" : "text-outline"}`}>
                {r.matches_scored} {r.matches_scored === 1 ? "match" : "matches"}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function LeaderboardList({ rows, loading, user }: { rows: Row[] | undefined; loading: boolean; user: string }) {
  if (loading && !rows) return <Skeletons rows={4} height={64} />;
  if (!rows?.length)
    return <EmptyPanel icon="leaderboard" title="No series teams yet" text="Teams built for the whole series are ranked here by points." />;
  return (
    <div className={`${card} p-space-lg`}>
      <LeaderboardRows rows={rows} user={user} />
    </div>
  );
}
