// Team score: not one of the four Stitch screens, built from the same components and tokens.
import { useState } from "react";
import { api, type MatchScore, type PlayerScore } from "../api";
import { Icon } from "../components/Icon";
import { scoreParts } from "../components/MatchCard";
import { Breadcrumb, btnSoft, ErrorBox, LivePill, MetricTile, RoleDot, Skeletons } from "../components/ui";
import { useRanks } from "../data";
import { pts, shortDate } from "../format";
import { navigate, useData } from "../hooks";
import { useUser } from "../user";

export function TeamPage({ teamId }: { teamId: number }) {
  const user = useUser();
  const score = useData((fresh) => api.score(teamId, fresh), [teamId]);
  const rankOf = useRanks(score.data ? [score.data.team] : []);

  if (score.loading && !score.data) return <Skeletons rows={3} height={200} />;
  if (score.error && !score.data) return <ErrorBox message={score.error} onRetry={() => score.reload(true)} />;

  const { team, matches, players, points } = score.data!;
  const mine = team.owner === user;
  const live = matches.some((m) => m.match.status === "LIVE");
  const locked = team.match_id !== null && matches.length > 0;
  const rank = rankOf(team);
  const byId = new Map(team.players.map((p) => [p.id, p]));
  const sorted = [...players].sort((a, b) => b.points - a.points);

  return (
    <div className="flex w-full flex-col gap-space-xl">
      <section className="relative overflow-hidden rounded-xl bg-surface-container-lowest p-space-lg shadow-sm lg:p-space-2xl">
        <div className="pointer-events-none absolute -top-24 -right-24 h-96 w-96 rounded-full bg-primary-container/10 blur-3xl" />
        <div className="relative z-10 flex flex-col gap-space-lg">
          <div className="flex flex-wrap items-center justify-between gap-space-sm">
            <Breadcrumb
              backTo={team.pool_id ? `/pools/${team.pool_id}` : "/teams"}
              label={team.pool_id ? "Pool" : "My Teams"}
              current={team.name}
            />
            {live ? (
              <LivePill label="Live now" soft />
            ) : (
              <span className="rounded-full bg-surface-container px-space-sm py-space-2xs font-label-badge text-label-badge tracking-wider text-secondary uppercase">
                {team.match_id ? "Match team" : "Series team"}
              </span>
            )}
          </div>
          <div className="flex flex-col justify-between gap-space-lg xl:flex-row xl:items-end">
            <div className="flex flex-col gap-space-xs">
              <h1 className="font-headline-xl-mobile text-headline-xl-mobile font-bold tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">
                {team.name}
              </h1>
              <div className="flex flex-wrap items-center gap-x-space-md gap-y-space-xs font-body-sm text-body-sm text-on-surface-variant">
                <div className="flex items-center gap-space-2xs">
                  <Icon name="emoji_events" className="text-[17px] text-outline" />
                  <span className="font-medium">{team.series_name}</span>
                </div>
                {!mine && (
                  <>
                    <span className="text-outline-variant">•</span>
                    <div className="flex items-center gap-space-2xs">
                      <Icon name="person" className="text-[17px] text-outline" />
                      <span>Manager: {team.owner}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
            {mine && (
              <div className="flex shrink-0 items-center gap-space-sm">
                <button
                  type="button"
                  disabled={locked}
                  onClick={() => navigate(`/teams/${team.id}/edit`)}
                  className={`${btnSoft} flex-1 px-space-lg py-space-sm sm:flex-none`}
                >
                  <Icon name={locked ? "lock" : "edit"} className="text-[18px]" />
                  <span>{locked ? "Squad Locked" : "Edit Team"}</span>
                </button>
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-space-sm sm:grid-cols-4">
            <MetricTile label="Total Points" accent value={pts(points)} />
            <MetricTile label="Standing" value={rank ? `#${rank.rank}` : "—"} sub={rank ? `/ ${rank.of}` : undefined} />
            <MetricTile label="Matches Scored" value={matches.length} />
            <MetricTile label="Players" value={team.players.length} />
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
        <div className="flex flex-col gap-space-lg lg:col-span-8">
          <h2 className="font-label-meta text-label-meta font-bold tracking-wider text-outline uppercase">Points by match</h2>
          {matches.length === 0 ? (
            <div className="rounded-xl bg-surface-container-lowest p-space-xl text-center font-body-md text-body-md text-outline shadow-sm">
              No matches have started yet. Points appear here as soon as one does.
            </div>
          ) : (
            [...matches].reverse().map((m, i) => <MatchBreakdown key={m.match.id} m={m} open={i === 0} />)
          )}
        </div>

        <aside className="flex flex-col gap-space-lg lg:col-span-4">
          <div className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
            <div className="flex items-center gap-space-xs">
              <Icon name="groups" className="text-[20px] text-primary" />
              <h2 className="font-headline-md text-[18px] font-bold text-on-surface">Squad Totals</h2>
            </div>
            <div className="flex flex-col gap-space-xs">
              {sorted.map((p) => (
                <div key={p.player_id} className="flex items-center justify-between rounded-lg bg-surface-container-low p-space-sm">
                  <div className="flex min-w-0 items-center gap-space-sm">
                    <RoleDot role={p.role} />
                    <div className="flex min-w-0 flex-col">
                      <span className="truncate font-body-sm text-body-sm font-bold text-on-surface">{p.name}</span>
                      <span className="truncate font-label-meta text-label-meta text-outline">{byId.get(p.player_id)?.team_name}</span>
                    </div>
                  </div>
                  <span className="shrink-0 font-label-numeric text-label-numeric font-bold text-on-surface">{pts(p.points)}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function MatchBreakdown({ m, open: initiallyOpen }: { m: MatchScore; open: boolean }) {
  const [open, setOpen] = useState(initiallyOpen);
  const live = m.match.status === "LIVE";
  return (
    <article className="relative overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm">
      {live && <div className="absolute top-0 bottom-0 left-0 w-1.5 bg-primary-container" />}
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-space-md p-space-lg text-left">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-space-xs">
            {live ? (
              <LivePill label="Live" soft />
            ) : (
              <span className="rounded bg-surface-container-low px-space-xs py-space-2xs font-label-badge text-label-badge font-bold text-outline uppercase">
                {shortDate(m.match.start)}
              </span>
            )}
          </div>
          <div className="truncate font-headline-md text-headline-md font-bold text-on-surface">
            {m.match.home.name} vs {m.match.away.name}
          </div>
          <div className="truncate font-body-sm text-body-sm text-outline">
            {m.match.result || [m.match.home.score, m.match.away.score].filter(Boolean).map((s) => scoreParts(s)[0]).join(" · ")}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-label-numeric text-[22px] font-bold text-primary">{pts(m.points)}</div>
          <div className="font-label-meta text-label-meta text-outline">pts</div>
        </div>
        <Icon name="expand_more" className={`shrink-0 text-[22px] text-outline transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="flex flex-col gap-space-xs px-space-lg pb-space-lg">
          {[...m.players].sort((a, b) => b.points - a.points).map((p) => (
            <PlayerLines key={p.player_id} p={p} />
          ))}
        </div>
      )}
    </article>
  );
}

function PlayerLines({ p }: { p: PlayerScore }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg bg-surface-container-low">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex min-h-12 w-full items-center gap-space-sm p-space-sm text-left">
        <RoleDot role={p.role} />
        <span className={`min-w-0 flex-1 truncate font-body-sm text-body-sm font-semibold ${p.played ? "text-on-surface" : "text-outline"}`}>
          {p.name}
          {!p.played && <span className="font-normal"> · didn't play</span>}
        </span>
        <span className="font-label-numeric text-label-numeric font-bold text-on-surface">{pts(p.points)}</span>
        <Icon name="expand_more" className={`text-[18px] text-outline transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="border-t border-surface-container px-space-sm pt-space-xs pb-space-sm font-body-sm text-body-sm">
          {p.lines.length === 0 ? (
            <p className="py-1 text-outline">No scoring events.</p>
          ) : (
            p.lines.map((l) => (
              <div key={l.key} className="flex justify-between gap-space-sm py-0.5">
                <span className="text-on-surface-variant">
                  {l.label}
                  {l.count > 1 && <span className="font-label-numeric"> ×{l.count}</span>}
                </span>
                <span className={`font-label-numeric ${l.points < 0 ? "text-error" : "text-on-surface"}`}>
                  {l.points > 0 ? `+${pts(l.points)}` : pts(l.points)}
                </span>
              </div>
            ))
          )}
          {p.multiplier !== 1 && (
            <div className="mt-space-xs flex justify-between border-t border-surface-container pt-space-xs font-semibold text-on-surface">
              <span>
                {pts(p.base)} × {p.multiplier}
              </span>
              <span className="font-label-numeric text-primary">{pts(p.points)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
