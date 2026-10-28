// Match cards from the series page design: live, upcoming and concluded variants.
import { api, type Match, type Team, type TeamScore } from "../api";
import { FORMAT_LABEL, pts, shortName, startTime, startsIn } from "../format";
import { useRef } from "react";
import { navigate, useData, useInView } from "../hooks";
import { Icon } from "./Icon";
import { btnPrimary, btnSoft, LivePill, sideCode, TeamCircle } from "./ui";

/** "176/7 (20.0)" -> ["176/7", "20.0 ov"]; multi-innings scores keep their "&" form. */
export function scoreParts(score: string): [string, string] {
  if (!score) return ["", ""];
  if (score.includes("&")) return [score.replace(/\s*\([^)]*\)/g, ""), ""];
  const m = score.match(/^(.*?)\s*\((.*)\)\s*$/);
  return m ? [m[1], `${m[2]} ov`] : [score, ""];
}

/** Whether ``side`` won, from a result line like "IND won by 4 wickets". */
function won(result: string, sideName: string): boolean {
  const r = result.toLowerCase();
  if (!r.includes("won")) return false;
  const first = r.split(" won")[0].trim();
  return first === sideName.toLowerCase() || first === sideCode(sideName).toLowerCase();
}

function Side({
  name,
  score,
  align,
  winner,
  sub,
}: {
  name: string;
  score: string;
  align: "left" | "right";
  winner?: boolean;
  sub?: string;
}) {
  const [runs, overs] = scoreParts(score);
  const right = align === "right";
  return (
    <div className={`flex items-center justify-between gap-space-md md:col-span-5 ${right ? "md:justify-end" : "md:justify-start"}`}>
      <div className={`flex items-center gap-space-sm ${right ? "md:order-2" : ""}`}>
        <span className={right ? "md:hidden" : ""}>
          <TeamCircle name={name} size="lg" />
        </span>
        <div className={`flex min-w-0 flex-col ${right ? "md:text-right" : ""}`}>
          <span className="font-headline-md text-headline-md font-bold text-on-surface">{name}</span>
          {sub && <span className={`font-label-meta text-label-meta ${winner ? "font-medium text-primary" : "text-outline"}`}>{sub}</span>}
        </div>
        {right && <span className="hidden md:inline-flex"><TeamCircle name={name} size="lg" /></span>}
      </div>
      {runs && (
        <div className={`shrink-0 text-right ${right ? "md:order-1 md:text-right" : "md:ml-auto"}`}>
          <div className={`font-label-numeric text-[20px] font-bold tracking-tight ${winner ? "text-primary" : "text-on-surface"}`}>{runs}</div>
          {overs && <div className={`font-label-numeric text-label-meta ${winner ? "font-medium text-primary" : "text-outline"}`}>{overs}</div>}
        </div>
      )}
    </div>
  );
}

function TopPerformer({ match }: { match: Match }) {
  // Scorecards are fetched only for cards on screen, so long lists don't flood the server.
  const ref = useRef<HTMLDivElement>(null);
  const visible = useInView(ref);
  const card = useData(
    () => (visible ? api.scorecard(match.series_id, match.id).catch(() => null) : Promise.resolve(undefined)),
    [match.id, match.status, visible],
  );
  const top = (card.data?.players ?? []).slice(0, 2);
  return (
    <div ref={ref} className="flex flex-col justify-between gap-space-xs rounded-lg bg-surface-container-low p-space-sm sm:flex-row sm:items-center">
      <div className="flex min-w-0 items-center gap-space-sm">
        <Icon name="bolt" className="text-[18px] text-primary" />
        <span className="min-w-0 font-body-sm text-body-sm font-medium text-on-surface">
          {(card.loading || !visible) && !card.data ? (
            <span className="skeleton inline-block h-4 w-48 align-middle" />
          ) : top.length ? (
            <>
              Top Performer:{" "}
              <strong className="font-semibold text-primary">
                {shortName(top[0].player.name)} ({pts(top[0].points)} pts)
              </strong>
              {top[1] && ` • ${shortName(top[1].player.name)} (${pts(top[1].points)} pts)`}
            </>
          ) : (
            "Player points appear as the match goes on."
          )}
        </span>
      </div>
      {match.status === "LIVE" && (
        <div className="flex items-center gap-space-xs font-label-numeric text-label-meta text-outline">
          <span className="h-1.5 w-1.5 rounded-full bg-primary-container" />
          <span>Tap Refresh for the latest</span>
        </div>
      )}
    </div>
  );
}

export function MatchCard({
  match,
  myTeam,
  myScore,
}: {
  match: Match;
  myTeam?: Team;
  myScore?: TeamScore | null;
}) {
  const scorecard = () => navigate(`/series/${match.series_id}/match/${match.id}`);
  const homeWon = match.status === "FT" && won(match.result, match.home.name);
  const awayWon = match.status === "FT" && won(match.result, match.away.name);
  const myPoints = myScore?.points;

  if (match.status === "NS")
    return (
      <article className="relative overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm transition-all hover:shadow-md">
        <div className="flex flex-col gap-space-md p-space-lg">
          <div className="flex flex-wrap items-center justify-between gap-space-xs">
            <div className="flex items-center gap-space-xs">
              <span className="rounded bg-surface-container px-space-xs py-space-2xs font-label-badge text-label-badge font-bold text-secondary uppercase">
                {FORMAT_LABEL[match.format] ?? "Upcoming"}
              </span>
              <span className="font-body-sm text-body-sm text-outline">•</span>
              <span className="font-body-sm text-body-sm text-outline">{startTime(match.start)}</span>
            </div>
            <div className="flex items-center gap-space-2xs rounded bg-tertiary-fixed px-space-xs py-space-2xs font-label-numeric text-label-numeric font-semibold text-on-tertiary-fixed">
              <Icon name="timer" className="text-[15px]" />
              <span>{startsIn(match.start)}</span>
            </div>
          </div>
          <div className="grid grid-cols-1 items-center gap-space-md py-space-xs md:grid-cols-12">
            <Side name={match.home.name} score="" align="left" sub="Home side" />
            <div className="flex flex-col items-center justify-center md:col-span-2">
              <span className="font-label-numeric text-label-numeric font-bold tracking-wider text-outline uppercase">VS</span>
              <span className="mt-0.5 font-label-numeric text-label-meta text-outline">
                {new Date(match.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} Local
              </span>
            </div>
            <Side name={match.away.name} score="" align="right" sub="Away side" />
          </div>
          <div className="grid grid-cols-1 gap-space-sm sm:grid-cols-2">
            <div className="flex items-center gap-space-xs rounded-lg bg-surface-container-low p-space-xs px-space-sm font-body-sm text-body-sm text-on-surface-variant">
              <Icon name="sports_baseball" className="text-[18px] text-outline" />
              <span>
                Pitch: <strong className="font-semibold text-on-surface">Report at the toss</strong>
              </span>
            </div>
            <div className="flex items-center gap-space-xs rounded-lg bg-surface-container-low p-space-xs px-space-sm font-body-sm text-body-sm text-on-surface-variant">
              <Icon name="lock_clock" className="text-[18px] text-outline" />
              <span>
                Teams lock: <strong className="font-semibold text-on-surface">at the start</strong>
              </span>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-space-sm pt-space-xs">
            <div className="flex items-center gap-space-xs font-label-meta text-label-meta text-on-surface-variant">
              <Icon name="groups" className="text-[16px] text-primary" />
              <span>{myTeam ? `Your team: ${myTeam.name}` : "Pick 11 from both squads"}</span>
            </div>
            <div className="flex w-full flex-nowrap items-center gap-space-xs sm:w-auto">
              <button type="button" onClick={scorecard} className={`${btnSoft} flex-1 sm:flex-none`}>
                <span>Match Center</span>
                <Icon name="arrow_forward" className="text-[16px]" />
              </button>
              <button
                type="button"
                onClick={() =>
                  navigate(myTeam ? `/teams/${myTeam.id}/edit` : `/series/${match.series_id}/build?match=${match.id}`)
                }
                className={`${btnPrimary} flex-1 sm:flex-none`}
              >
                <Icon name={myTeam ? "edit" : "add"} className="text-[18px]" />
                <span>{myTeam ? "Edit Match XI" : "Create Match XI"}</span>
              </button>
            </div>
          </div>
        </div>
      </article>
    );

  const live = match.status === "LIVE";
  return (
    <article className={`relative overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm transition-all hover:shadow-md ${live ? "" : "opacity-95"}`}>
      {live && <div className="absolute top-0 bottom-0 left-0 w-1.5 bg-primary-container" />}
      <div className={`flex flex-col gap-space-md p-space-lg ${live ? "pl-space-xl" : ""}`}>
        <div className="flex flex-wrap items-center justify-between gap-space-xs">
          <div className="flex flex-wrap items-center gap-space-xs">
            <span
              className={`rounded px-space-xs py-space-2xs font-label-badge text-label-badge font-bold uppercase ${
                live ? "bg-surface-container text-on-surface" : "bg-surface-container-low text-outline"
              }`}
            >
              {FORMAT_LABEL[match.format] ?? (live ? "In Play" : "Concluded")}
            </span>
            <span className="font-body-sm text-body-sm text-outline">•</span>
            <span className="font-body-sm text-body-sm text-outline">{startTime(match.start)}</span>
          </div>
          {live ? (
            <LivePill label="Live coverage" soft />
          ) : (
            <div className="flex items-center gap-space-2xs font-label-numeric text-label-numeric text-outline">
              <Icon name="check_circle" className="text-[15px]" />
              <span>Completed</span>
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 items-center gap-space-md py-space-xs md:grid-cols-12">
          <Side name={match.home.name} score={match.home.score} align="left" winner={homeWon} sub={homeWon ? "Won" : match.home.score ? "Batted" : "Yet to bat"} />
          <div className="flex flex-col items-center justify-center py-space-xs md:col-span-2">
            <span className="font-label-numeric text-label-numeric font-bold tracking-wider text-outline uppercase">VS</span>
            {match.result && (
              <span className="mt-1 rounded bg-primary-container/15 px-space-xs py-space-2xs text-center font-label-meta text-[10px] font-bold text-on-primary-container">
                {match.result.toUpperCase()}
              </span>
            )}
          </div>
          <Side name={match.away.name} score={match.away.score} align="right" winner={awayWon} sub={awayWon ? "Won" : match.away.score ? "Batted" : "Yet to bat"} />
        </div>

        {myTeam && myPoints !== undefined ? (
          <div className="flex flex-col justify-between gap-space-xs rounded-lg bg-surface-container-low p-space-sm sm:flex-row sm:items-center">
            <div className="flex items-center gap-space-sm">
              <Icon name="stars" className="text-[20px] text-secondary" />
              <span className="font-body-sm text-body-sm font-medium text-on-surface">
                {live ? "Your squad has" : "Your squad earned"}{" "}
                <strong className="font-label-numeric font-bold text-primary">{pts(myPoints)} pts</strong>
              </span>
            </div>
            {(() => {
              const c = myScore?.players.find((p) => p.role === "captain");
              return c ? (
                <span className="rounded bg-surface-container px-space-xs py-space-2xs font-label-meta text-[11px] font-semibold text-secondary">
                  Captain: {c.name} ({pts(c.points)} pts)
                </span>
              ) : null;
            })()}
          </div>
        ) : (
          <TopPerformer match={match} />
        )}

        <div className="flex flex-wrap items-center justify-between gap-space-sm pt-space-xs">
          <div className="flex items-center gap-space-xs">
            {myTeam && myPoints !== undefined && (
              <div className="flex items-center gap-space-2xs rounded-lg bg-surface-container px-space-sm py-space-xs">
                <Icon name="shield_person" className="text-[18px] text-primary" />
                <span className="font-body-sm text-body-sm font-semibold text-on-surface">My Match Squad:</span>
                <span className="font-label-numeric text-label-numeric font-bold text-primary">{pts(myPoints)} pts</span>
              </div>
            )}
          </div>
          <div className="flex w-full flex-nowrap items-center justify-end gap-space-xs sm:w-auto">
            {myTeam && (
              <button type="button" onClick={() => navigate(`/teams/${myTeam.id}`)} className={`${btnSoft} flex-1 sm:flex-none`}>
                <Icon name="analytics" className="text-[16px]" />
                <span>Team Breakdown</span>
              </button>
            )}
            <button type="button" onClick={scorecard} className={`${btnSoft} flex-1 sm:flex-none`}>
              {live ? <Icon name="visibility" className="text-[16px]" /> : null}
              <span>{live ? "Scorecard" : "Full Scorecard"}</span>
              {!live && <Icon name="arrow_forward" className="text-[16px]" />}
            </button>
            {live && !myTeam && (
              <span className="flex flex-1 cursor-not-allowed items-center justify-center gap-space-2xs rounded-lg bg-surface-container-low px-space-md py-space-xs font-body-sm text-body-sm font-medium text-on-surface-variant sm:flex-none">
                <Icon name="lock" className="text-[16px]" />
                <span>Squad Locked</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
