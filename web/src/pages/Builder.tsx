// "Team builder (create & edit)" from the Stitch design (web/design/team_builder_create_edit).
import { useEffect, useMemo, useState } from "react";
import {
  api,
  ApiError,
  peek,
  type Match,
  type Player,
  type PoolKind,
  type PoolTeamIn,
  type Position,
  type Role,
  type Series,
} from "../api";
import { Icon } from "../components/Icon";
import { ErrorBox, MultiplierButton, RoleBadge, sideCode, Skeletons } from "../components/ui";
import { initials, POSITION_ORDER, ROLE_SHORT, shortName, startsIn } from "../format";
import { back, navigate, useData } from "../hooks";

/** Dream Team pools: Dream11-style limits (kept in sync with fantasy/service.py DreamTeamRules). */
export const DREAM = {
  players: 11,
  maxFromOneSide: 7,
  roles: { wicket_keeper: [1, 4], batter: [3, 6], all_rounder: [1, 4], bowler: [3, 6] } as Record<Position, [number, number]>,
};
const NORMAL_POOL_MAX = 30;

/** A team being drafted inside the create-pool form (not saved until the pool is). */
export interface Draft {
  kind: PoolKind;
  initial?: PoolTeamIn;
  onDone: (team: PoolTeamIn) => void;
  onCancel: () => void;
}

/**
 * Create or edit a team. Standalone teams use the API's limits; pool teams follow their pool's
 * type ("normal": no rules, "dream": Dream11 rules). ``draft`` returns the team to the
 * create-pool form instead of saving it.
 */
export function Builder({
  seriesId,
  matchId,
  teamId,
  poolId,
  draft,
}: {
  seriesId: number;
  matchId: number | null;
  teamId?: number;
  poolId?: number;
  draft?: Draft;
}) {
  const existing = useData(() => (teamId ? api.team(teamId) : Promise.resolve(null)), [teamId]);
  const team = existing.data ?? null;
  const pid = poolId ?? team?.pool_id ?? null;
  const poolQ = useData(() => (pid ? api.pool(pid) : Promise.resolve(null)), [pid]);
  const pool = poolQ.data?.pool ?? null;
  // Wait for the team (editing) or the pool (adding to a pool) before loading squads.
  const ready = (!teamId || team !== null) && (!poolId || pool !== null);
  const sid = team ? team.series_id : poolId && pool ? pool.series_id : seriesId;
  const mid = team ? team.match_id : poolId && pool ? pool.match_id : matchId;
  const kind: PoolKind | null = draft?.kind ?? pool?.type ?? null;

  const rules = useData(() => api.rules(), []);
  const matches = useData(() => (ready ? api.matches(sid) : Promise.resolve(undefined)), [ready, sid]);
  const players = useData(() => (ready ? api.players(sid, mid) : Promise.resolve(undefined)), [ready, sid, mid]);

  const [name, setName] = useState("");
  const [picked, setPicked] = useState<Map<number, Role>>(new Map());
  const [loadedFrom, setLoadedFrom] = useState<number | null>(null);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    if (team && loadedFrom !== team.id) {
      setName(team.name);
      setPicked(new Map(team.players.map((p) => [p.id, p.role])));
      setLoadedFrom(team.id);
    }
  }, [team, loadedFrom]);
  useEffect(() => {
    if (draft?.initial && loadedFrom === null) {
      setName(draft.initial.name);
      setPicked(new Map(draft.initial.players.map((p) => [p.player_id, p.role])));
      setLoadedFrom(-1);
    }
  }, [draft, loadedFrom]);

  const [side, setSide] = useState<number | "all">("all");
  const [role, setRole] = useState<Position | "all">("all");
  const [query, setQuery] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const max = kind === "dream" ? DREAM.players : kind === "normal" ? NORMAL_POOL_MAX : (rules.data?.team_max_players ?? 11);
  const min = kind === "dream" ? DREAM.players : kind === "normal" ? 1 : (rules.data?.team_min_players ?? 1);
  const match: Match | undefined = matches.data?.find((m) => m.id === mid);
  const locked = !!mid && !!match && match.status !== "NS";
  const seriesName =
    peek<Series[]>("/api/series")?.find((s) => s.id === sid)?.name ?? match?.series_name ?? matches.data?.[0]?.series_name ?? "";

  const all = players.data ?? [];
  const byId = useMemo(() => new Map(all.map((p) => [p.id, p])), [all]);
  const sides = useMemo(() => {
    const seen = new Map<number, string>();
    for (const p of all) seen.set(p.team_id, p.team_name);
    return [...seen.entries()].map(([id, label]) => ({ id, label, total: all.filter((p) => p.team_id === id).length }));
  }, [all]);
  const list = useMemo(() => {
    const q = query.trim().toLowerCase();
    return all
      .filter((p) => side === "all" || p.team_id === side)
      .filter((p) => role === "all" || p.position === role)
      .filter((p) => !q || `${p.name} ${p.team_name}`.toLowerCase().includes(q))
      .sort(
        (a, b) =>
          Number(picked.has(b.id)) - Number(picked.has(a.id)) ||
          a.team_name.localeCompare(b.team_name) ||
          POSITION_ORDER.indexOf(a.position) - POSITION_ORDER.indexOf(b.position) ||
          a.name.localeCompare(b.name),
      );
    // Picked players float to the top only when the filters change, not on every tap.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [all, side, role, query, loadedFrom]);

  const count = picked.size;
  const holder = (r: Role) => [...picked.entries()].find(([, v]) => v === r)?.[0];
  const captain = holder("captain");
  const vice = holder("vice_captain");
  const pickedPlayers = [...picked.keys()].map((id) => byId.get(id)).filter(Boolean) as Player[];
  const perSide = (id: number) => pickedPlayers.filter((p) => p.team_id === id).length;
  const perRole = (pos: Position) => pickedPlayers.filter((p) => p.position === pos).length;
  // Dream Team checks, shown live; other teams only need a size in range.
  const roleBad = (pos: Position) => {
    const [lo, hi] = DREAM.roles[pos];
    return perRole(pos) < lo || perRole(pos) > hi;
  };
  const sideOver = !!mid && sides.some((s) => perSide(s.id) > DREAM.maxFromOneSide);
  const dreamProblem =
    kind !== "dream"
      ? null
      : count !== DREAM.players
        ? `Pick exactly ${DREAM.players} players`
        : !captain || !vice
          ? "Pick a captain and vice-captain"
          : POSITION_ORDER.some(roleBad)
            ? "Role limits not met (see the counts above)"
            : sideOver
              ? `At most ${DREAM.maxFromOneSide} players from one side`
              : null;
  const valid = kind === "dream" ? !dreamProblem : count >= min && count <= max && (kind === "normal" || (!!captain && !!vice));

  function toggle(p: Player) {
    setError(null);
    setDirty(true);
    setPicked((prev) => {
      const next = new Map(prev);
      if (next.has(p.id)) next.delete(p.id);
      else if (next.size < max) next.set(p.id, "player");
      else setError(`You can pick up to ${max} players.`);
      return next;
    });
  }

  function assign(p: Player, r: Exclude<Role, "player">) {
    setDirty(true);
    setPicked((prev) => {
      const next = new Map(prev);
      const current = next.get(p.id);
      for (const [id, v] of next) if (v === r) next.set(id, "player");
      next.set(p.id, current === r ? "player" : r);
      return next;
    });
  }

  async function save() {
    setSaving(true);
    setError(null);
    const body = {
      name: name.trim() || "My XI",
      players: [...picked.entries()].map(([player_id, r]) => ({ player_id, role: r })),
    };
    if (draft) {
      draft.onDone(body);
      return;
    }
    try {
      if (team) {
        await api.editTeam(team.id, body);
        navigate(team.pool_id ? `/pools/${team.pool_id}` : `/teams/${team.id}`, true);
      } else if (poolId) {
        await api.addPoolTeam(poolId, body);
        navigate(`/pools/${poolId}`, true);
      } else {
        const saved = await api.createTeam({ ...body, series_id: sid, match_id: mid });
        navigate(`/teams/${saved.id}`, true);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save the team.");
      setSaving(false);
    }
  }

  const ring = 125.66;
  const title = match ? `${match.home.name} vs ${match.away.name}` : team ? "Series team" : "Series team";

  if (existing.error) return <ErrorBox message={existing.error} onRetry={() => existing.reload(true)} />;

  return (
    <div className="flex w-full flex-col pb-28">
      {/* Context & deadline banner */}
      <div className="relative mb-space-lg overflow-hidden rounded-xl bg-surface-container-low p-space-md shadow-sm">
        <div className="pointer-events-none absolute -top-8 -right-8 h-44 w-44 rounded-full bg-primary-container/10 blur-2xl" />
        <div className="relative z-10 flex flex-col justify-between gap-space-sm md:flex-row md:items-center">
          <div className="flex min-w-0 items-center gap-space-sm">
            <button
              type="button"
              onClick={() => (draft ? draft.onCancel() : back(pid ? `/pools/${pid}` : `/series/${sid}`))}
              aria-label="Back"
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-container-lowest text-primary shadow-sm"
            >
              <Icon name="arrow_back" className="text-[20px]" />
            </button>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-space-xs">
                <span className="truncate font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase">
                  {pool ? `${pool.name} · ${kind === "dream" ? "Dream Team pool" : "Normal pool"}` : draft ? (kind === "dream" ? "New Dream Team pool" : "New normal pool") : seriesName}
                </span>
                <span className="text-xs text-outline">•</span>
                <span className="font-headline-md text-headline-md font-bold text-on-surface">{title}</span>
              </div>
              <p className="mt-0.5 flex items-center gap-1.5 font-body-sm text-body-sm text-on-surface-variant">
                <Icon name={locked ? "lock" : "timer"} className="text-[16px] text-tertiary" />
                {locked ? (
                  <span>The match has started, so this team is locked.</span>
                ) : match ? (
                  <span>
                    Deadline: <strong className="font-semibold text-on-surface">{startsIn(match.start)}</strong> — teams lock at the start
                  </span>
                ) : (
                  <span>A series team can be edited any time; points count for every match.</span>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-space-sm self-stretch rounded-lg bg-surface-container-lowest px-space-md py-space-xs shadow-sm md:self-auto">
            <div className="flex min-w-0 flex-1 items-center gap-1.5">
              <input
                aria-label="Team name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setDirty(true);
                }}
                disabled={locked}
                maxLength={40}
                placeholder="Name your team"
                className="w-full min-w-0 bg-transparent font-body-md text-body-md font-semibold text-ellipsis text-on-surface placeholder:text-outline focus:outline-none md:w-48"
              />
              <Icon name="edit" className="text-[16px] text-outline" />
            </div>
            <div className="h-4 w-px bg-surface-container-highest" />
            <div className={`flex shrink-0 items-center gap-1 font-label-meta text-label-meta font-medium ${dirty ? "text-outline" : "text-primary"}`}>
              <Icon name={dirty ? "edit_note" : "cloud_done"} className="text-[15px]" />
              <span>{team ? (dirty ? "Unsaved changes" : "Saved") : "New team"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* HUD */}
      <div className="mb-space-lg rounded-xl bg-surface-container-lowest p-space-md shadow-sm lg:p-space-lg">
        <div className="grid grid-cols-1 items-center gap-space-md lg:grid-cols-12">
          <div className="flex items-center gap-space-md lg:col-span-4">
            <div className="relative flex h-14 w-14 shrink-0 items-center justify-center">
              <svg className="h-14 w-14 -rotate-90" viewBox="0 0 48 48">
                <circle className="text-surface-container" cx="24" cy="24" fill="transparent" r="20" stroke="currentColor" strokeWidth="4.5" />
                <circle
                  className="text-primary-container transition-all duration-300"
                  cx="24"
                  cy="24"
                  fill="transparent"
                  r="20"
                  stroke="currentColor"
                  strokeDasharray={ring}
                  strokeDashoffset={ring * (1 - Math.min(1, count / max))}
                  strokeLinecap="round"
                  strokeWidth="4.5"
                />
              </svg>
              <span className="absolute font-label-numeric text-headline-md font-bold text-on-surface">{count}</span>
            </div>
            <div className="flex flex-col">
              <span className="font-headline-md text-headline-md leading-tight font-bold text-on-surface">
                {count} / {max} <span className="font-body-sm text-body-sm font-normal text-outline">Selected</span>
              </span>
              <span className={`flex items-center gap-1 font-label-meta text-label-meta font-semibold ${valid ? "text-primary" : "text-outline"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${valid ? "bg-primary-container" : "bg-outline-variant"}`} />
                {valid
                  ? kind === "normal"
                    ? "Ready to save (no team rules in this pool)"
                    : "Valid team, ready to save"
                  : (dreamProblem ?? (!captain || !vice ? "Pick a captain and vice-captain" : `Pick ${min}-${max} players`))}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-start gap-space-sm lg:col-span-8 lg:justify-end">
            {sides.length > 0 && (
              <div className="flex items-center gap-space-xs rounded-lg bg-surface-container-low px-space-md py-space-xs">
                {sides.slice(0, 2).map((s, i) => (
                  <div key={s.id} className="flex items-center gap-1.5">
                    {i > 0 && <span className="mr-1 text-xs text-outline">•</span>}
                    <span className={`h-2.5 w-2.5 rounded-full ${i === 0 ? "bg-primary" : "bg-tertiary-container"}`} />
                    <span className="font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase">{sideCode(s.label)}</span>
                    <span className="font-label-numeric text-label-numeric font-bold text-on-surface">{perSide(s.id)}</span>
                  </div>
                ))}
                {sides.length > 2 && <span className="font-label-meta text-label-meta text-outline">+{sides.length - 2} teams</span>}
              </div>
            )}
            <div className="flex items-center gap-space-xs rounded-lg bg-surface-container-low px-space-md py-space-xs">
              <Icon name="toll" className="text-[16px] text-primary" />
              <span className="font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase">Credits Left:</span>
              <span className="font-label-numeric text-label-numeric font-bold text-on-surface">—</span>
            </div>
            <div className="flex items-center gap-space-xs">
              <div className="flex items-center gap-1 rounded-md bg-surface-container-high px-space-sm py-space-2xs">
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-on-surface font-label-badge text-[9px] font-bold text-surface">C</span>
                <span className="max-w-[80px] truncate font-body-sm text-body-sm font-semibold text-on-surface">
                  {captain ? shortName(byId.get(captain)?.name ?? "") : "—"}
                </span>
                <span className="font-label-badge text-label-badge font-bold text-primary-container">{rules.data?.captain ?? 2}x</span>
              </div>
              <div className="flex items-center gap-1 rounded-md bg-surface-container-high px-space-sm py-space-2xs">
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-secondary font-label-badge text-[9px] font-bold text-surface">VC</span>
                <span className="max-w-[80px] truncate font-body-sm text-body-sm font-semibold text-on-surface">
                  {vice ? shortName(byId.get(vice)?.name ?? "") : "—"}
                </span>
                <span className="font-label-badge text-label-badge font-bold text-on-surface-variant">{rules.data?.vice_captain ?? 1.5}x</span>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-space-md grid grid-cols-2 gap-space-sm border-t border-surface-container-high/60 pt-space-sm sm:grid-cols-4">
          {POSITION_ORDER.map((pos) => (
            <div key={pos} className="flex items-center justify-between rounded-lg bg-surface-container-low/80 p-space-xs">
              <span className="font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase">
                {ROLE_SHORT[pos]}
                {kind === "dream" && ` (${DREAM.roles[pos][0]}-${DREAM.roles[pos][1]})`}
              </span>
              <span className={`flex items-center gap-1 font-label-numeric text-label-numeric font-bold ${kind === "dream" && roleBad(pos) && count > 0 ? "text-error" : "text-on-surface"}`}>
                <span>{perRole(pos)}</span>
                {(kind === "dream" ? !roleBad(pos) : perRole(pos) > 0) && <Icon name="check_circle" className="text-[14px] text-primary" />}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Multiplier hint */}
      <div className="mb-space-md flex flex-wrap items-center justify-between gap-2 rounded-lg bg-surface-container-high/60 p-space-xs px-space-md">
        <div className="flex items-center gap-2 font-body-sm text-body-sm text-on-surface-variant">
          <Icon name="stars" className="text-[18px] text-primary" />
          <span>
            Assign your multipliers: <strong className="font-semibold text-on-surface">C</strong> grants{" "}
            <strong>{rules.data?.captain ?? 2}x points</strong>, <strong className="font-semibold text-on-surface">VC</strong> grants{" "}
            <strong>{rules.data?.vice_captain ?? 1.5}x points</strong>.
          </span>
        </div>
        <span className="font-label-meta text-label-meta font-medium text-outline">Tap the C/VC tags on picked players</span>
      </div>

      {/* Filters */}
      <div className="mb-space-md flex flex-col items-stretch justify-between gap-space-sm rounded-xl bg-surface-container-lowest p-space-md shadow-sm md:flex-row md:items-center">
        <div className="no-scrollbar flex items-center self-start overflow-x-auto rounded-lg bg-surface-container-low p-1">
          {[{ id: "all" as const, label: "All", total: all.length }, ...sides].map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSide(s.id)}
              className={`shrink-0 rounded-md px-space-md py-space-xs font-body-sm text-body-sm whitespace-nowrap transition-all ${
                side === s.id ? "bg-surface-container-lowest font-semibold text-on-surface shadow-sm" : "font-medium text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {s.label} ({s.total})
            </button>
          ))}
        </div>
        <div className="relative max-w-sm flex-1">
          <Icon name="search" className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-[18px] text-outline" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search player name or team..."
            className="w-full rounded-lg bg-surface-container-low py-space-xs pr-3 pl-9 font-body-sm text-body-sm text-on-surface placeholder:text-outline focus:ring-2 focus:ring-primary-container focus:outline-none"
            style={{ minHeight: 36 }}
          />
        </div>
        <div className="no-scrollbar flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
          {(["all", ...POSITION_ORDER] as const).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRole(r)}
              className={`shrink-0 rounded-lg px-space-sm py-space-2xs font-body-sm text-body-sm whitespace-nowrap transition-all ${
                role === r ? "bg-primary-container font-semibold text-on-primary-container" : "bg-surface-container-low font-medium text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {r === "all" ? "All Roles" : ROLE_SHORT[r]}
            </button>
          ))}
        </div>
      </div>

      {/* Player list */}
      <div className="overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm">
        <div className="hidden bg-surface-container-low px-space-md py-space-sm font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase md:grid md:grid-cols-12">
          <div className="col-span-5">Player / Team</div>
          <div className="col-span-2 text-center">Selected %</div>
          <div className="col-span-1 text-center">Form</div>
          <div className="col-span-1 text-center">Credits</div>
          <div className="col-span-2 text-center">Multiplier (C / VC)</div>
          <div className="col-span-1 text-right">Roster</div>
        </div>
        {!ready || (players.loading && !players.data) ? (
          <div className="p-space-md">
            <Skeletons rows={6} height={56} />
          </div>
        ) : players.error && !players.data ? (
          <div className="p-space-md">
            <ErrorBox message={players.error} onRetry={() => players.reload(true)} />
          </div>
        ) : list.length === 0 ? (
          <p className="p-space-xl text-center font-body-md text-body-md text-outline">No players match.</p>
        ) : (
          <div className="flex flex-col divide-y divide-surface-container-low">
            {list.map((p, i) => {
              const r = picked.get(p.id);
              const isIn = r !== undefined;
              const sideIdx = sides.findIndex((s) => s.id === p.team_id);
              return (
                <div
                  key={p.id}
                  className={`flex flex-col gap-space-sm p-space-md transition-colors md:grid md:grid-cols-12 md:items-center md:py-space-sm ${
                    isIn ? "bg-surface-container-lowest" : "bg-surface-container-lowest/60 hover:bg-surface-container-low/50"
                  } ${!isIn && count >= max ? "opacity-75" : ""}`}
                  style={i > 60 ? { contentVisibility: "auto", containIntrinsicSize: "0 96px" } : undefined}
                >
                  <div className="flex items-center gap-space-sm md:col-span-5">
                    <div className="relative shrink-0">
                      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-high font-label-badge text-label-badge text-on-surface-variant">
                        {initials(p.name)}
                      </span>
                      <span
                        className={`absolute -right-2 -bottom-1.5 rounded px-1 py-px font-label-badge text-[8px] font-bold ${
                          sideIdx === 0 ? "bg-primary text-on-primary" : "bg-tertiary text-on-tertiary"
                        }`}
                      >
                        {sideCode(p.team_name)}
                      </span>
                    </div>
                    <div className="flex min-w-0 flex-col">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="truncate font-body-md text-body-md font-semibold text-on-surface">{p.name}</span>
                        <RoleBadge position={p.position} />
                      </div>
                      <span className="font-body-sm text-body-sm text-outline">{p.team_name}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between md:contents">
                    <div className="md:col-span-2 md:text-center">
                      <span className="mr-2 font-label-meta text-label-meta text-outline md:hidden">SEL:</span>
                      <span className="font-label-numeric text-label-numeric font-medium text-outline">—</span>
                    </div>
                    <div className="md:col-span-1 md:text-center">
                      <span className="mr-2 font-label-meta text-label-meta text-outline md:hidden">FORM:</span>
                      <span className="font-label-numeric text-label-numeric font-semibold text-outline">—</span>
                    </div>
                    <div className="md:col-span-1 md:text-center">
                      <span className="mr-2 font-label-meta text-label-meta text-outline md:hidden">CR:</span>
                      <span className="font-label-numeric text-label-numeric font-bold text-outline">—</span>
                    </div>
                    <div className="flex items-center gap-1.5 md:col-span-2 md:justify-center">
                      <MultiplierButton kind="C" active={r === "captain"} disabled={!isIn || locked} onClick={() => assign(p, "captain")} />
                      <MultiplierButton kind="VC" active={r === "vice_captain"} disabled={!isIn || locked} onClick={() => assign(p, "vice_captain")} />
                    </div>
                    <div className="flex justify-end md:col-span-1">
                      <button
                        type="button"
                        disabled={locked || (!isIn && count >= max)}
                        onClick={() => toggle(p)}
                        aria-label={isIn ? `Remove ${p.name}` : `Add ${p.name}`}
                        className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors md:h-8 md:w-8 ${
                          isIn
                            ? "bg-primary-container text-on-primary-container hover:bg-error-container hover:text-on-error-container"
                            : "bg-surface-container-low text-on-surface-variant hover:bg-primary-container hover:text-on-primary-container"
                        }`}
                      >
                        <Icon name={isIn ? "check" : "add"} className="text-[18px]" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Sticky drawer (above the phone's bottom navigation) */}
      <div className="pb-safe fixed right-0 bottom-16 left-0 z-40 bg-surface-container-lowest/95 p-space-sm px-gutter shadow-xl backdrop-blur-xl lg:bottom-0 lg:left-60 lg:px-gutter-desktop">
        {error && <p className="mx-auto mb-space-xs max-w-7xl font-body-sm text-body-sm text-error">{error}</p>}
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-space-sm sm:flex-row">
          <div className="flex w-full items-center justify-between gap-space-sm sm:w-auto sm:justify-start">
            <div className="flex items-center gap-2">
              <span className={`inline-flex h-2.5 w-2.5 rounded-full bg-primary-container ${valid ? "animate-pulse" : "opacity-40"}`} />
              <span className="font-body-md text-body-md font-bold text-on-surface">
                {count}/{max} selected
              </span>
            </div>
            <div className="hidden h-4 w-px bg-surface-container-highest sm:block" />
            <div className="flex min-w-0 items-center gap-1.5 font-body-sm text-body-sm text-on-surface-variant">
              <span className="truncate">
                C: <strong className="text-on-surface">{captain ? shortName(byId.get(captain)?.name ?? "") : "—"}</strong>
              </span>
              <span>•</span>
              <span className="truncate">
                VC: <strong className="text-on-surface">{vice ? shortName(byId.get(vice)?.name ?? "") : "—"}</strong>
              </span>
            </div>
          </div>
          <div className="flex w-full items-center justify-end gap-space-sm sm:w-auto">
            {count > 0 && !locked && (
              <button
                type="button"
                onClick={() => {
                  setPicked(new Map());
                  setDirty(true);
                }}
                className="flex items-center gap-1 rounded-lg px-space-md py-space-sm font-body-sm text-body-sm font-semibold text-on-surface-variant transition-colors hover:bg-error-container/20 hover:text-error sm:py-space-xs"
              >
                <Icon name="restart_alt" className="text-[16px]" />
                <span>Reset XI</span>
              </button>
            )}
            <button
              type="button"
              disabled={locked || saving || !name.trim() || (kind === "dream" ? !valid : count < min)}
              onClick={save}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary-container px-space-lg py-space-sm font-body-sm text-body-sm font-semibold text-on-primary-container shadow-sm transition-all hover:bg-primary hover:text-on-primary active:scale-[0.98] disabled:opacity-50 sm:flex-none sm:py-space-xs"
            >
              <span>{saving ? "Saving…" : draft ? "Add to Pool" : team ? "Save Changes" : poolId ? "Add Team" : "Save Team"}</span>
              <Icon name="arrow_forward" className="text-[18px]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
