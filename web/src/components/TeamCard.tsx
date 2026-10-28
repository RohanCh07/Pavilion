// Team cards from the "My Teams" design: live, series and upcoming variants.
import { useState } from "react";
import { api, ApiError, type Match, type Team, type TeamScore } from "../api";
import { POSITION_ORDER, pts, ROLE_SHORT, shortName, startTime, startsIn } from "../format";
import { navigate, useData } from "../hooks";
import { Icon } from "./Icon";
import { btnPrimary, btnSoft } from "./ui";

type State = "live" | "series" | "upcoming" | "finished";

function stateOf(team: Team, matches: Match[]): { state: State; match?: Match; next?: Match } {
  const next = matches.filter((m) => m.status === "NS").sort((a, b) => a.start.localeCompare(b.start))[0];
  if (team.match_id !== null) {
    const match = matches.find((m) => m.id === team.match_id);
    if (!match) return { state: "upcoming" };
    return { state: match.status === "LIVE" ? "live" : match.status === "FT" ? "finished" : "upcoming", match };
  }
  const live = matches.find((m) => m.status === "LIVE");
  if (live) return { state: "live", match: live, next };
  if (!next && matches.length && matches.every((m) => m.status === "FT")) return { state: "finished" };
  return { state: "series", next };
}

export function teamState(team: Team, matches: Match[]): State {
  return stateOf(team, matches).state;
}

export function TeamCard({
  team,
  score,
  rank,
  onDeleted,
}: {
  team: Team;
  score: TeamScore | null | undefined;
  rank: { rank: number; of: number } | null;
  onDeleted?: () => void;
}) {
  const matches = useData(() => api.matches(team.series_id), [team.series_id]);
  const { state, match, next } = stateOf(team, matches.data ?? []);
  const [busy, setBusy] = useState(false);
  const locked = team.match_id !== null && state !== "upcoming";

  const captain = team.players.find((p) => p.role === "captain");
  const vice = team.players.find((p) => p.role === "vice_captain");
  const totalOf = (id?: number) => score?.players.find((p) => p.player_id === id)?.points;
  // Momentum needs at least two matches to say anything.
  const perMatch = (score?.matches.length ?? 0) > 1 ? score!.matches.slice(-7).map((m) => m.points) : [];
  const peak = Math.max(1, ...perMatch);
  const last = score?.matches.at(-1);

  async function remove() {
    if (!confirm(`Delete "${team.name}"? This can't be undone.`)) return;
    setBusy(true);
    try {
      await api.deleteTeam(team.id);
      onDeleted?.();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Couldn't delete the team.");
      setBusy(false);
    }
  }

  function share() {
    const url = `${location.origin}${location.pathname}#/teams/${team.id}`;
    if (navigator.share) navigator.share({ title: team.name, url }).catch(() => {});
    else navigator.clipboard?.writeText(url).then(() => alert("Link copied"));
  }

  const banner =
    state === "live" ? (
      <div className="flex flex-wrap items-center justify-between gap-space-sm bg-primary-container/15 px-space-lg py-space-xs">
        <div className="flex items-center gap-space-sm">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-container opacity-85" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
          </span>
          <span className="font-label-badge text-label-badge font-bold tracking-wider text-on-primary-container uppercase">
            Live now{match ? ` · ${match.home.name} vs ${match.away.name}` : ""}
          </span>
        </div>
        <div className="flex items-center gap-space-xs font-label-numeric text-label-numeric font-semibold text-primary">
          <Icon name="bolt" className="text-[16px]" />
          <span>Tap Refresh for the latest</span>
        </div>
      </div>
    ) : state === "series" ? (
      <div className="flex flex-wrap items-center justify-between gap-space-sm bg-surface-container px-space-lg py-space-xs">
        <div className="flex items-center gap-space-sm">
          <span className="rounded bg-surface-container-lowest px-space-xs py-space-2xs font-label-badge text-label-badge font-bold tracking-wider text-on-surface uppercase">
            Active Series Squad
          </span>
          <span className="font-label-numeric text-label-numeric font-medium text-on-surface-variant">
            {score ? `${score.matches.length} ${score.matches.length === 1 ? "match" : "matches"} scored` : "…"}
          </span>
        </div>
        {next && (
          <div className="flex items-center gap-space-xs font-label-numeric text-label-numeric font-medium text-on-surface-variant">
            <Icon name="history" className="text-[16px] text-outline" />
            <span className="truncate">Next: {startTime(next.start)}</span>
          </div>
        )}
      </div>
    ) : state === "upcoming" ? (
      <div className="flex flex-wrap items-center justify-between gap-space-sm bg-surface-container-low px-space-lg py-space-xs">
        <div className="flex items-center gap-space-sm">
          <span className="rounded bg-surface-container-high px-space-xs py-space-2xs font-label-badge text-label-badge font-bold tracking-wider text-on-surface-variant uppercase">
            Upcoming{match ? ` · ${startsIn(match.start)}` : ""}
          </span>
          {match && <span className="font-label-numeric text-label-numeric font-medium text-outline">{startTime(match.start)}</span>}
        </div>
        <div className="flex items-center gap-space-xs font-label-numeric text-label-numeric font-semibold text-primary">
          <Icon name="check_circle" className="text-[16px]" />
          <span>Draft ready</span>
        </div>
      </div>
    ) : (
      <div className="flex flex-wrap items-center justify-between gap-space-sm bg-surface-container-low px-space-lg py-space-xs">
        <span className="rounded bg-surface-container-high px-space-xs py-space-2xs font-label-badge text-label-badge font-bold tracking-wider text-outline uppercase">
          Finished
        </span>
        {match?.result && <span className="truncate font-label-numeric text-label-numeric text-outline">{match.result}</span>}
      </div>
    );

  const roles = POSITION_ORDER.map((p) => [ROLE_SHORT[p], team.players.filter((x) => x.position === p).length] as const);

  return (
    <div
      className={`relative w-full overflow-hidden rounded-2xl bg-surface-container-lowest transition-all duration-200 ${
        state === "live" ? "shadow-md hover:shadow-lg" : "shadow-sm hover:shadow-md"
      }`}
    >
      {banner}
      <div className="flex flex-col gap-space-lg p-space-lg lg:p-space-xl">
        {/* Header + score */}
        <div className="flex flex-col justify-between gap-space-md lg:flex-row lg:items-center">
          <div className="flex min-w-0 items-start gap-space-md">
            <div
              className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${
                state === "upcoming" ? "bg-surface-container-low text-secondary" : "bg-surface-container text-primary"
              }`}
            >
              <Icon name={team.match_id ? "sports_cricket" : "shield"} className="text-[32px]" />
            </div>
            <div className="flex min-w-0 flex-col">
              <div className="flex items-center gap-space-xs">
                <h2 className="truncate font-headline-md text-headline-md font-bold text-on-surface">{team.name}</h2>
                <span
                  className={`shrink-0 rounded px-space-xs py-space-2xs font-label-badge text-label-badge font-bold ${
                    team.match_id ? "bg-surface-container text-on-surface-variant" : "bg-secondary-container text-on-secondary-container"
                  }`}
                >
                  {team.match_id ? "MATCH" : "SERIES"}
                </span>
              </div>
              <p className="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-space-xs font-body-sm text-body-sm text-on-surface-variant">
                <span className="truncate font-medium text-on-surface">{team.series_name}</span>
                {match && team.match_id && (
                  <>
                    <span>•</span>
                    <span>
                      {match.home.name} vs {match.away.name}
                    </span>
                  </>
                )}
              </p>
            </div>
          </div>
          {state === "upcoming" ? (
            <div className="flex items-center gap-space-sm self-start rounded-xl bg-surface-container-low px-space-md py-space-sm">
              {roles.map(([label, n], i) => (
                <div key={label} className="flex items-center gap-space-sm">
                  {i > 0 && <span className="text-surface-container-high">•</span>}
                  <div className="flex flex-col items-center">
                    <span className="font-label-meta text-label-meta text-outline uppercase">{label}</span>
                    <span className="font-label-numeric text-label-numeric font-bold text-on-surface">{n}</span>
                  </div>
                </div>
              ))}
              <div className="ml-space-xs h-6 w-px bg-surface-container-high" />
              <div className="ml-space-xs flex flex-col">
                <span className="font-label-meta text-label-meta text-outline uppercase">Players</span>
                <span className="font-label-numeric text-label-numeric font-bold text-primary">{team.players.length}</span>
              </div>
            </div>
          ) : (
            <div className="flex items-baseline gap-space-md self-start rounded-xl bg-surface-container-low px-space-lg py-space-sm">
              <div className="flex flex-col">
                <span className="font-label-meta text-label-meta font-semibold text-outline uppercase">
                  {team.match_id ? "Total Points" : "Series Total"}
                </span>
                <div className="flex items-baseline gap-space-xs">
                  <span className="font-label-numeric text-headline-xl-mobile font-bold tracking-tight text-on-surface md:text-headline-xl">
                    {score === undefined ? "…" : pts(score?.points ?? 0)}
                  </span>
                  {last && score && score.matches.length > 1 ? (
                    <span className="inline-flex items-center font-label-numeric text-label-numeric font-semibold text-primary">
                      <Icon name="arrow_upward" className="text-[14px]" />+{pts(last.points)} last match
                    </span>
                  ) : (
                    <span className="font-label-numeric text-label-numeric text-outline">pts</span>
                  )}
                </div>
              </div>
              <div className="h-8 w-px bg-surface-container-high" />
              <div className="flex flex-col">
                <span className="font-label-meta text-label-meta font-semibold text-outline uppercase">
                  {team.match_id ? "Contest Rank" : "Standing"}
                </span>
                <div className="flex items-baseline gap-space-2xs">
                  <span className="font-label-numeric text-headline-md font-bold text-primary">{rank ? `#${rank.rank}` : "—"}</span>
                  {rank && <span className="font-label-numeric text-label-numeric font-normal text-outline">/ {rank.of}</span>}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Leadership multipliers + momentum */}
        {(captain || vice) && (
          <div className="grid grid-cols-1 gap-space-md md:grid-cols-12">
            <div className={`flex flex-col gap-space-xs ${perMatch.length ? "md:col-span-8" : "md:col-span-12"}`}>
              <span className="font-label-meta text-label-meta font-bold tracking-wider text-outline uppercase">Leadership Multipliers</span>
              <div className="grid grid-cols-1 gap-space-sm sm:grid-cols-2">
                {[captain, vice].map((p) => {
                  if (!p) return null;
                  const isC = p.role === "captain";
                  const total = totalOf(p.id);
                  const mult = isC ? 2 : 1.5;
                  return (
                    <div key={p.id} className="flex items-center justify-between rounded-xl bg-surface-container-low p-space-sm transition-colors hover:bg-surface-container">
                      <div className="flex min-w-0 items-center gap-space-sm">
                        <div className="relative shrink-0">
                          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-high font-label-badge text-label-badge text-on-surface-variant">
                            {p.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                          </span>
                          <span
                            className={`absolute -right-1 -bottom-1 flex h-5 min-w-5 items-center justify-center rounded-full px-0.5 font-label-badge text-[9px] font-black shadow-sm ${
                              isC ? "bg-tertiary-container text-on-primary-fixed" : "bg-secondary text-on-secondary"
                            }`}
                          >
                            {isC ? "2x" : "1.5x"}
                          </span>
                        </div>
                        <div className="flex min-w-0 flex-col">
                          <div className="flex items-center gap-space-2xs">
                            <span className="truncate font-body-sm text-body-sm font-bold text-on-surface">{shortName(p.name)}</span>
                            <span className="rounded bg-surface-container-highest px-1 font-label-badge text-[10px] font-bold text-on-surface-variant">
                              {ROLE_SHORT[p.position]}
                            </span>
                          </div>
                          <span className="font-label-meta text-label-meta text-outline">
                            {total === undefined ? p.team_name : `${pts(total / mult)} pts base score`}
                          </span>
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className={`font-label-numeric text-label-numeric font-bold ${isC ? "text-primary" : "text-secondary"}`}>
                          {total === undefined ? "—" : `${pts(total)} pts`}
                        </span>
                        <span className="block font-label-meta text-label-meta text-outline">{isC ? "Captain" : "Vice-captain"}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            {perMatch.length > 0 && (
              <div className="flex flex-col justify-between rounded-xl bg-surface-container-low p-space-sm md:col-span-4">
                <div className="flex items-center justify-between">
                  <span className="font-label-meta text-label-meta font-bold tracking-wider text-outline uppercase">Points Momentum</span>
                  <span className="font-label-numeric text-label-numeric font-bold text-primary">{perMatch.length} played</span>
                </div>
                <div className="flex h-10 items-end gap-1.5 py-space-2xs">
                  {perMatch.map((v, i) => (
                    <div
                      key={i}
                      className={`w-full rounded-t-sm ${
                        i === perMatch.length - 1 ? "bg-primary-container" : i === perMatch.length - 2 ? "bg-primary-container/60" : "bg-surface-container-high"
                      }`}
                      style={{ height: `${Math.max(8, (v / peak) * 100)}%` }}
                      title={`${pts(v)} pts`}
                    />
                  ))}
                </div>
                <div className="flex justify-between font-label-meta text-label-meta text-outline">
                  <span>Match 1</span>
                  <span className="font-semibold text-primary">Latest</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap items-center justify-between gap-space-sm pt-space-sm">
          {locked ? (
            <div className="flex items-center gap-space-xs font-label-meta text-label-meta text-outline">
              <Icon name="lock" className="text-[16px] text-tertiary" />
              <span>Squad locked at the start of the match</span>
            </div>
          ) : (
            <button
              type="button"
              onClick={remove}
              disabled={busy}
              className="inline-flex items-center gap-space-2xs py-1 font-body-sm text-body-sm font-medium text-error hover:underline"
            >
              <Icon name="delete" className="text-[18px]" />
              <span>{team.match_id ? "Delete Team" : "Disband Squad"}</span>
            </button>
          )}
          <div className="ml-auto flex w-full items-center gap-space-sm sm:w-auto">
            <button
              type="button"
              onClick={share}
              title="Share team"
              aria-label="Share team"
              className="rounded-lg p-space-xs text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface"
            >
              <Icon name="share" className="text-[20px]" />
            </button>
            <button type="button" disabled={locked} onClick={() => navigate(`/teams/${team.id}/edit`)} className={`${btnSoft} flex-1 sm:flex-none`}>
              <Icon name={locked ? "lock" : "edit"} className="text-[18px]" />
              <span>{locked ? "Edit Squad" : "Edit Team"}</span>
            </button>
            <button
              type="button"
              onClick={() => navigate(`/teams/${team.id}`)}
              className={
                state === "live"
                  ? "inline-flex flex-1 items-center justify-center gap-space-xs rounded-lg bg-primary px-space-lg py-space-xs font-body-sm text-body-sm font-semibold text-on-primary shadow-sm transition-all hover:bg-on-primary-container sm:flex-none"
                  : `${btnPrimary} flex-1 sm:flex-none`
              }
            >
              <Icon name={state === "live" ? "sports_score" : "analytics"} className="text-[18px]" />
              <span>{state === "live" ? "Live Score" : "View Score"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
