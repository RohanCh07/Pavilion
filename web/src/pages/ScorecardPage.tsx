// Match scorecard with points: built from the design's tokens and components.
import { useMemo, useState } from "react";
import { api, type ScorecardPlayer } from "../api";
import { Icon } from "../components/Icon";
import { scoreParts } from "../components/MatchCard";
import { Breadcrumb, ErrorBox, LivePill, RoleBadge, Segmented, sideCode, Skeletons, TeamCircle } from "../components/ui";
import { FORMAT_LABEL, pts, startTime } from "../format";
import { useData } from "../hooks";

const n = (s: ScorecardPlayer, k: string) => Number(s.stats[k] ?? 0);
const overs = (balls: number) => `${Math.floor(balls / 6)}.${balls % 6}`;

/** A player's key numbers in one line, e.g. "51 (26)* 6×4 1×6 · 2 ct". */
function summary(p: ScorecardPlayer): string {
  const parts: string[] = [];
  if (p.stats.batted) {
    let bat = `${n(p, "runs")} (${n(p, "balls_faced")})${p.stats.out ? "" : "*"}`;
    const b = [n(p, "fours") && `${n(p, "fours")}×4`, n(p, "sixes") && `${n(p, "sixes")}×6`].filter(Boolean).join(" ");
    if (b) bat += ` ${b}`;
    parts.push(bat);
  }
  if (n(p, "balls_bowled"))
    parts.push(`${n(p, "wickets")}-${n(p, "runs_conceded")} (${overs(n(p, "balls_bowled"))})${n(p, "maidens") ? ` ${n(p, "maidens")}m` : ""}`);
  const ro = n(p, "run_outs_direct") + n(p, "run_outs_assisted");
  const field = [n(p, "catches") && `${n(p, "catches")} ct`, n(p, "stumpings") && `${n(p, "stumpings")} st`, ro && `${ro} ro`].filter(Boolean);
  if (field.length) parts.push(field.join(" "));
  return parts.join(" · ") || (p.stats.in_xi ? "In the XI" : "—");
}

export function ScorecardPage({ seriesId, matchId }: { seriesId: number; matchId: number }) {
  const { data, error, loading, reload } = useData((fresh) => api.scorecard(seriesId, matchId, fresh), [seriesId, matchId]);
  const [side, setSide] = useState<string>("all");
  const players = useMemo(() => (data?.players ?? []).filter((p) => side === "all" || String(p.player.team_id) === side), [data, side]);

  if (loading && !data) return <Skeletons rows={3} height={180} />;
  if (error && !data) return <ErrorBox message={error} onRetry={() => reload(true)} />;

  const m = data!.match;
  return (
    <div className="flex w-full flex-col gap-space-xl">
      <section className="relative overflow-hidden rounded-xl bg-surface-container-lowest p-space-lg shadow-sm lg:p-space-2xl">
        <div className="pointer-events-none absolute -top-24 -right-24 h-96 w-96 rounded-full bg-primary-container/10 blur-3xl" />
        <div className="relative z-10 flex flex-col gap-space-lg">
          <div className="flex flex-wrap items-center justify-between gap-space-sm">
            <Breadcrumb backTo={`/series/${seriesId}`} label={m.series_name || "Series"} current="Scorecard" />
            {m.status === "LIVE" ? (
              <LivePill label="Live now" soft />
            ) : (
              <span className="rounded-full bg-surface-container px-space-sm py-space-2xs font-label-badge text-label-badge tracking-wider text-secondary uppercase">
                {m.status === "FT" ? "Concluded" : "Upcoming"}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-space-xs">
            <h1 className="font-headline-xl-mobile text-headline-xl-mobile font-bold tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">
              {m.home.name} vs {m.away.name}
            </h1>
            <div className="flex flex-wrap items-center gap-x-space-md gap-y-space-xs font-body-sm text-body-sm text-on-surface-variant">
              <div className="flex items-center gap-space-2xs">
                <Icon name="calendar_today" className="text-[17px] text-outline" />
                <span>{startTime(m.start)}</span>
              </div>
              <span className="text-outline-variant">•</span>
              <div className="flex items-center gap-space-2xs">
                <Icon name="sports_cricket" className="text-[17px] text-outline" />
                <span className="font-label-numeric text-label-numeric font-semibold text-primary">
                  {FORMAT_LABEL[m.format] ?? "T20"} scoring rules
                </span>
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-space-sm rounded-xl bg-surface-container-low p-space-md">
            {[m.home, m.away].map((s) => {
              const [runs, ov] = scoreParts(s.score);
              return (
                <div key={s.id} className="flex items-center justify-between gap-space-sm">
                  <div className="flex min-w-0 items-center gap-space-sm">
                    <TeamCircle name={s.name} size="lg" />
                    <span className="truncate font-headline-md text-headline-md font-bold text-on-surface">{s.name}</span>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="font-label-numeric text-[20px] font-bold text-on-surface">{runs || "—"}</div>
                    {ov && <div className="font-label-numeric text-label-meta text-outline">{ov}</div>}
                  </div>
                </div>
              );
            })}
            {m.result && (
              <p className="flex items-center gap-1 font-body-sm text-body-sm font-semibold text-primary">
                <Icon name="check_circle" className="text-[16px]" /> {m.result}
              </p>
            )}
          </div>
        </div>
      </section>

      <Segmented
        value={side}
        onChange={setSide}
        options={[
          { value: "all", label: "All Players", count: data!.players.length },
          { value: String(m.home.id), label: sideCode(m.home.name) },
          { value: String(m.away.id), label: sideCode(m.away.name) },
        ]}
      />

      <div className="overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm">
        <div className="hidden bg-surface-container-low px-space-md py-space-sm font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase md:grid md:grid-cols-12">
          <div className="col-span-5">Player</div>
          <div className="col-span-5">Match Stats</div>
          <div className="col-span-2 text-right">Fantasy Pts</div>
        </div>
        {players.length === 0 ? (
          <p className="p-space-xl text-center font-body-md text-body-md text-outline">
            {m.status === "NS" ? "Stats appear once the match starts." : "No player stats yet."}
          </p>
        ) : (
          <div className="flex flex-col divide-y divide-surface-container-low">
            {players.map((p) => (
              <div key={p.player.id} className="flex items-center gap-space-sm p-space-md md:grid md:grid-cols-12 md:py-space-sm">
                <div className="flex min-w-0 flex-1 flex-col md:col-span-5">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-body-md text-body-md font-semibold text-on-surface">{p.player.name}</span>
                    <RoleBadge position={p.player.position} />
                  </div>
                  <span className="font-body-sm text-body-sm text-outline md:hidden">{summary(p)}</span>
                  <span className="hidden font-body-sm text-body-sm text-outline md:block">{p.player.team_name}</span>
                </div>
                <div className="hidden font-label-numeric text-label-numeric text-on-surface-variant md:col-span-5 md:block">{summary(p)}</div>
                <div className="shrink-0 text-right md:col-span-2">
                  <span className="font-label-numeric text-[18px] font-bold text-primary">{pts(p.points)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <p className="-mt-space-md px-space-xs font-label-meta text-label-meta text-outline">Points before captain and vice-captain multipliers.</p>
    </div>
  );
}
