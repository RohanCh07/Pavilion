// Pools: groups of fantasy teams for one series or match, each with its own leaderboard.
// Built from the design's My Teams and leaderboard components.
import { useState } from "react";
import { api, ApiError, type Match, type Pool, type PoolKind, type PoolTeamIn, type Series } from "../api";
import { Icon } from "../components/Icon";
import { Breadcrumb, btnPrimary, btnSoft, EmptyPanel, ErrorBox, MetricTile, RoleDot, Skeletons } from "../components/ui";
import { pts, startTime } from "../format";
import { back, navigate, useData } from "../hooks";
import { useUser } from "../user";
import { Builder } from "./Builder";

const KIND_LABEL: Record<PoolKind, string> = { normal: "Normal", dream: "Dream Team" };

function KindBadge({ kind }: { kind: PoolKind }) {
  return (
    <span
      className={`shrink-0 rounded px-space-xs py-space-2xs font-label-badge text-label-badge font-bold uppercase ${
        kind === "dream" ? "bg-tertiary-fixed text-on-tertiary-fixed" : "bg-secondary-container text-on-secondary-container"
      }`}
    >
      {KIND_LABEL[kind]}
    </span>
  );
}

// --- List -----------------------------------------------------------------------------------

export function Pools() {
  const user = useUser();
  const pools = useData((fresh) => api.myPools(fresh), [user]);

  return (
    <div className="flex w-full flex-col">
      <div className="mb-space-xl flex flex-col justify-between gap-space-lg md:flex-row md:items-end">
        <div className="flex flex-col">
          <div className="mb-space-2xs flex items-center gap-space-xs text-outline">
            <span className="font-label-meta text-label-meta font-semibold tracking-wider uppercase">Pavilion Pools</span>
          </div>
          <h1 className="font-headline-xl-mobile text-headline-xl-mobile tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">
            My Pools
          </h1>
          <p className="mt-space-2xs max-w-2xl font-body-md text-body-md text-on-surface-variant">
            Group teams for a series or a single match and see who's on top. Normal pools have no rules; Dream Team pools
            follow Dream11's team rules.
          </p>
        </div>
        <button type="button" onClick={() => navigate("/pools/new")} className={`${btnPrimary} w-full px-space-lg py-space-sm md:w-auto`}>
          <Icon name="add_circle" className="text-[20px]" />
          <span>Create Pool</span>
        </button>
      </div>

      {pools.loading && !pools.data ? (
        <Skeletons rows={2} height={160} />
      ) : pools.error && !pools.data ? (
        <ErrorBox message={pools.error} onRetry={() => pools.reload(true)} />
      ) : !pools.data?.length ? (
        <EmptyPanel
          icon="groups"
          title="No pools yet"
          text="Create a pool for a series or a match, add your teams, and track the pool's leaderboard."
          action={
            <button type="button" onClick={() => navigate("/pools/new")} className={`${btnPrimary} px-space-xl py-space-sm`}>
              <Icon name="add" className="text-[18px]" />
              <span>Create Pool</span>
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-space-lg lg:grid-cols-2">
          {pools.data.map((p) => (
            <PoolCard key={p.id} pool={p} />
          ))}
        </div>
      )}
    </div>
  );
}

function PoolCard({ pool }: { pool: Pool }) {
  const detail = useData(() => api.pool(pool.id), [pool.id]);
  const top = detail.data?.leaderboard.slice(0, 3) ?? [];
  return (
    <button
      type="button"
      onClick={() => navigate(`/pools/${pool.id}`)}
      className="flex w-full flex-col gap-space-md rounded-2xl bg-surface-container-lowest p-space-lg text-left shadow-sm transition-all hover:shadow-md"
    >
      <div className="flex items-start gap-space-md">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-surface-container text-primary">
          <Icon name="groups" className="text-[28px]" />
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center gap-space-xs">
            <h2 className="truncate font-headline-md text-headline-md font-bold text-on-surface">{pool.name}</h2>
            <KindBadge kind={pool.type} />
          </div>
          <p className="truncate font-body-sm text-body-sm text-on-surface-variant">
            {pool.series_name} · {pool.match_id ? "Single match" : "Whole series"}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-label-numeric text-headline-md font-bold text-on-surface">{pool.team_count}</div>
          <div className="font-label-meta text-label-meta text-outline uppercase">Teams</div>
        </div>
      </div>
      {top.length > 0 && (
        <div className="flex flex-col gap-space-xs">
          {top.map((r) => (
            <div key={r.team.id} className="flex items-center justify-between rounded-lg bg-surface-container-low px-space-sm py-space-xs">
              <span className="flex min-w-0 items-center gap-space-sm">
                <span className="font-label-numeric text-label-numeric font-bold text-outline">#{r.rank}</span>
                <span className="truncate font-body-sm text-body-sm font-semibold text-on-surface">{r.team.name}</span>
              </span>
              <span className="font-label-numeric text-label-numeric font-bold text-primary">{pts(r.points)}</span>
            </div>
          ))}
        </div>
      )}
    </button>
  );
}

// --- Detail ---------------------------------------------------------------------------------

export function PoolPage({ poolId }: { poolId: number }) {
  const user = useUser();
  const detail = useData((fresh) => api.pool(poolId, fresh), [poolId]);
  const [busy, setBusy] = useState(false);
  const pool = detail.data?.pool;
  const matches = useData(() => (pool ? api.matches(pool.series_id) : Promise.resolve(undefined)), [pool?.series_id]);

  if (detail.loading && !detail.data) return <Skeletons rows={3} height={180} />;
  if (detail.error && !detail.data) return <ErrorBox message={detail.error} onRetry={() => detail.reload(true)} />;

  const { leaderboard } = detail.data!;
  const p = pool!;
  const mine = p.owner === user;
  const match = matches.data?.find((m) => m.id === p.match_id);
  const locked = !!match && match.status !== "NS";
  const leader = leaderboard[0];

  async function rename() {
    const name = prompt("Pool name", p.name)?.trim();
    if (!name || name === p.name) return;
    try {
      await api.renamePool(p.id, name);
      detail.reload(true);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Couldn't rename the pool.");
    }
  }

  async function remove() {
    if (!confirm(`Delete "${p.name}" and all ${leaderboard.length} of its teams? This can't be undone.`)) return;
    setBusy(true);
    try {
      await api.deletePool(p.id);
      navigate("/pools", true);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Couldn't delete the pool.");
      setBusy(false);
    }
  }

  return (
    <div className="flex w-full flex-col gap-space-xl">
      <section className="relative overflow-hidden rounded-xl bg-surface-container-lowest p-space-lg shadow-sm lg:p-space-2xl">
        <div className="pointer-events-none absolute -top-24 -right-24 h-96 w-96 rounded-full bg-primary-container/10 blur-3xl" />
        <div className="relative z-10 flex flex-col gap-space-lg">
          <div className="flex flex-wrap items-center justify-between gap-space-sm">
            <Breadcrumb backTo="/pools" label="Pools" current={p.name} />
            <KindBadge kind={p.type} />
          </div>
          <div className="flex flex-col justify-between gap-space-lg xl:flex-row xl:items-end">
            <div className="flex flex-col gap-space-xs">
              <h1 className="font-headline-xl-mobile text-headline-xl-mobile font-bold tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">
                {p.name}
              </h1>
              <div className="flex flex-wrap items-center gap-x-space-md gap-y-space-xs font-body-sm text-body-sm text-on-surface-variant">
                <div className="flex items-center gap-space-2xs">
                  <Icon name="emoji_events" className="text-[17px] text-outline" />
                  <span className="font-medium">{p.series_name}</span>
                </div>
                <span className="text-outline-variant">•</span>
                <div className="flex items-center gap-space-2xs">
                  <Icon name="sports_cricket" className="text-[17px] text-outline" />
                  <span>{match ? `${match.home.name} vs ${match.away.name} · ${startTime(match.start)}` : "Whole series"}</span>
                </div>
                {!mine && (
                  <>
                    <span className="text-outline-variant">•</span>
                    <span>Created by {p.owner}</span>
                  </>
                )}
              </div>
            </div>
            {mine && (
              <div className="flex shrink-0 flex-wrap items-center gap-space-sm">
                <button
                  type="button"
                  disabled={locked}
                  onClick={() => navigate(`/pools/${p.id}/add`)}
                  className={`${btnPrimary} flex-1 px-space-lg py-space-sm sm:flex-none`}
                >
                  <Icon name={locked ? "lock" : "add"} className="text-[18px]" />
                  <span>{locked ? "Pool Locked" : "Add Team"}</span>
                </button>
                <button type="button" onClick={rename} className={`${btnSoft} py-space-sm`}>
                  <Icon name="edit" className="text-[18px]" />
                  <span>Rename</span>
                </button>
                <button type="button" onClick={remove} disabled={busy} aria-label="Delete pool" className={`${btnSoft} py-space-sm text-error`}>
                  <Icon name="delete" className="text-[18px]" />
                </button>
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-space-sm sm:grid-cols-4">
            <MetricTile label="Teams" value={leaderboard.length} />
            <MetricTile label="Leader" accent value={leader ? pts(leader.points) : "—"} sub={leader?.team.name} />
            <MetricTile label="Matches Scored" value={leader?.matches_scored ?? 0} />
            <MetricTile label="Pool Type" value={KIND_LABEL[p.type]} />
          </div>
        </div>
      </section>

      <div className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
        <div className="flex items-center gap-space-xs">
          <Icon name="leaderboard" className="text-[20px] text-primary" />
          <h2 className="font-headline-md text-[18px] font-bold text-on-surface">Pool Leaderboard</h2>
        </div>
        <p className="-mt-space-xs font-body-sm text-body-sm text-on-surface-variant">
          Tap a team for its player-by-player points. {locked ? "The match has started, so teams are locked." : ""}
        </p>
        {leaderboard.length === 0 ? (
          <p className="py-space-md text-center font-body-md text-body-md text-outline">No teams yet. Add the first one.</p>
        ) : (
          <div className="flex flex-col gap-space-xs">
            {leaderboard.map((r) => (
              <div key={r.team.id} className="flex items-center gap-space-sm rounded-lg bg-surface-container-low p-space-sm">
                <button type="button" onClick={() => navigate(`/teams/${r.team.id}`)} className="flex min-w-0 flex-1 items-center gap-space-sm text-left">
                  <span
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-label-numeric text-[12px] font-bold ${
                      r.rank === 1
                        ? "bg-tertiary-fixed text-on-tertiary-fixed"
                        : r.rank === 2
                          ? "bg-secondary-fixed text-on-secondary-fixed"
                          : "bg-surface-container text-on-surface"
                    }`}
                  >
                    {r.rank}
                  </span>
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate font-body-md text-body-md font-bold text-on-surface">{r.team.name}</span>
                    <span className="flex min-w-0 items-center gap-space-xs font-label-meta text-label-meta text-outline">
                      <span>{r.team.players.length} players</span>
                      {r.captain && (
                        <span className="flex min-w-0 items-center gap-1">
                          · <RoleDot role="captain" /> <span className="truncate">{r.captain}</span>
                        </span>
                      )}
                    </span>
                  </span>
                </button>
                <span className="shrink-0 font-label-numeric text-[18px] font-bold text-primary">{pts(r.points)}</span>
                {mine && !locked && (
                  <button
                    type="button"
                    onClick={() => navigate(`/teams/${r.team.id}/edit`)}
                    aria-label={`Edit ${r.team.name}`}
                    className="rounded-lg p-space-xs text-outline hover:bg-surface-container hover:text-on-surface"
                  >
                    <Icon name="edit" className="text-[18px]" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- Create ---------------------------------------------------------------------------------

export function PoolCreate({ seriesId, matchId }: { seriesId: number | null; matchId: number | null }) {
  const series = useData(() => api.series(), []);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<PoolKind>("normal");
  const [sid, setSid] = useState<number | null>(seriesId);
  const [mid, setMid] = useState<number | null>(matchId);
  const [teams, setTeams] = useState<PoolTeamIn[]>([]);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const matches = useData(() => (sid ? api.matches(sid) : Promise.resolve([] as Match[])), [sid]);
  const upcoming = (matches.data ?? []).filter((m) => m.status === "NS");
  const list: Series[] = (series.data ?? []).filter((s) => s.status !== "finished");

  if (editing !== null && sid)
    return (
      <Builder
        key={`draft-${editing}`}
        seriesId={sid}
        matchId={mid}
        draft={{
          kind,
          initial: editing === "new" ? undefined : teams[editing],
          onCancel: () => setEditing(null),
          onDone: (team) => {
            setTeams((prev) => (editing === "new" ? [...prev, team] : prev.map((t, i) => (i === editing ? team : t))));
            setEditing(null);
            window.scrollTo(0, 0);
          },
        }}
      />
    );

  const missing = !name.trim() ? "Name the pool" : !sid ? "Pick a series" : kind === "normal" && teams.length === 0 ? "Add at least one team" : null;

  async function create() {
    if (!sid || missing) return;
    setSaving(true);
    setError(null);
    try {
      const made = await api.createPool({ name: name.trim(), type: kind, series_id: sid, match_id: mid, teams });
      navigate(`/pools/${made.pool.id}`, true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create the pool.");
      setSaving(false);
    }
  }

  const label = "mb-space-xs block font-label-meta text-label-meta font-semibold tracking-wider text-outline uppercase";
  const field =
    "w-full rounded-lg bg-surface-container-low px-space-md py-space-sm font-body-md text-body-md text-on-surface placeholder:text-outline focus:ring-2 focus:ring-primary-container focus:outline-none";

  return (
    <div className="flex w-full flex-col gap-space-lg pb-28">
      <div className="flex flex-col">
        <Breadcrumb backTo="/pools" label="Pools" current="New pool" />
        <h1 className="mt-space-sm font-headline-xl-mobile text-headline-xl-mobile tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">
          Create Pool
        </h1>
      </div>

      <section className="flex flex-col gap-space-lg rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
        <div>
          <label className={label} htmlFor="pool-name">
            Pool name
          </label>
          <input id="pool-name" value={name} maxLength={40} onChange={(e) => setName(e.target.value)} placeholder="e.g. Office League" className={field} />
        </div>

        <div>
          <span className={label}>Pool type</span>
          <div className="grid grid-cols-1 gap-space-sm sm:grid-cols-2">
            {(
              [
                ["normal", "Normal", "No rules: any number of players, captain optional, the same player in many teams. Needs at least one team."],
                ["dream", "Dream Team", "Dream11 rules: 11 players with a captain and vice-captain, 1-4 WK, 3-6 BAT, 1-4 AR, 3-6 BOWL, max 7 from one side."],
              ] as const
            ).map(([value, title, text]) => (
              <button
                key={value}
                type="button"
                disabled={teams.length > 0 && kind !== value}
                onClick={() => setKind(value)}
                aria-pressed={kind === value}
                className={`flex flex-col gap-space-2xs rounded-xl p-space-md text-left transition-all disabled:opacity-50 ${
                  kind === value ? "bg-primary-container/15 ring-2 ring-primary-container" : "bg-surface-container-low hover:bg-surface-container"
                }`}
              >
                <span className="flex items-center gap-space-xs font-body-md text-body-md font-bold text-on-surface">
                  <Icon name={kind === value ? "check_circle" : value === "dream" ? "stars" : "groups"} className={`text-[20px] ${kind === value ? "text-primary" : "text-outline"}`} />
                  {title}
                </span>
                <span className="font-body-sm text-body-sm text-on-surface-variant">{text}</span>
              </button>
            ))}
          </div>
          {teams.length > 0 && <p className="mt-space-xs font-label-meta text-label-meta text-outline">Remove the teams below to change the type.</p>}
        </div>

        <div className="grid grid-cols-1 gap-space-md sm:grid-cols-2">
          <div>
            <label className={label} htmlFor="pool-series">
              Series
            </label>
            <select
              id="pool-series"
              value={sid ?? ""}
              disabled={teams.length > 0}
              onChange={(e) => {
                setSid(Number(e.target.value) || null);
                setMid(null);
              }}
              className={field}
            >
              <option value="">Choose a series</option>
              {list.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={label} htmlFor="pool-match">
              Scope
            </label>
            <select
              id="pool-match"
              value={mid ?? ""}
              disabled={!sid || teams.length > 0}
              onChange={(e) => setMid(Number(e.target.value) || null)}
              className={field}
            >
              <option value="">Whole series</option>
              {upcoming.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.home.name} vs {m.away.name} · {startTime(m.start)}
                </option>
              ))}
            </select>
          </div>
        </div>
        {teams.length > 0 && <p className="-mt-space-sm font-label-meta text-label-meta text-outline">Series and scope are fixed once teams are added.</p>}
      </section>

      <section className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
        <div className="flex items-center justify-between gap-space-sm">
          <div className="flex items-center gap-space-xs">
            <Icon name="groups" className="text-[20px] text-primary" />
            <h2 className="font-headline-md text-[18px] font-bold text-on-surface">Pool Teams</h2>
            <span className="rounded-full bg-surface-container px-space-xs py-space-2xs font-label-numeric text-[11px]">{teams.length}</span>
          </div>
          <span className="font-label-meta text-label-meta text-outline">{kind === "normal" ? "At least 1 required" : "Optional now"}</span>
        </div>
        {teams.map((t, i) => {
          const c = t.players.find((p) => p.role === "captain");
          return (
            <div key={i} className="flex items-center gap-space-sm rounded-lg bg-surface-container-low p-space-sm">
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="truncate font-body-md text-body-md font-bold text-on-surface">{t.name}</span>
                <span className="font-label-meta text-label-meta text-outline">
                  {t.players.length} players{c ? " · captain picked" : ""}
                </span>
              </div>
              <button type="button" onClick={() => setEditing(i)} aria-label={`Edit ${t.name}`} className="rounded-lg p-space-xs text-outline hover:text-on-surface">
                <Icon name="edit" className="text-[18px]" />
              </button>
              <button
                type="button"
                onClick={() => setTeams(teams.filter((_, j) => j !== i))}
                aria-label={`Remove ${t.name}`}
                className="rounded-lg p-space-xs text-outline hover:text-error"
              >
                <Icon name="delete" className="text-[18px]" />
              </button>
            </div>
          );
        })}
        <button type="button" disabled={!sid} onClick={() => setEditing("new")} className={`${btnSoft} w-full py-space-sm`}>
          <Icon name="add" className="text-[18px]" />
          <span>{sid ? "Add Team" : "Pick a series first"}</span>
        </button>
      </section>

      {/* Sticky create bar */}
      <div className="pb-safe fixed right-0 bottom-16 left-0 z-40 bg-surface-container-lowest/95 p-space-sm px-gutter shadow-xl backdrop-blur-xl lg:bottom-0 lg:left-60 lg:px-gutter-desktop">
        {error && <p className="mx-auto mb-space-xs max-w-7xl font-body-sm text-body-sm text-error">{error}</p>}
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-space-sm">
          <span className="font-body-sm text-body-sm text-on-surface-variant">{missing ?? `${teams.length} team${teams.length === 1 ? "" : "s"} ready`}</span>
          <div className="flex items-center gap-space-sm">
            <button type="button" onClick={() => back("/pools")} className="rounded-lg px-space-md py-space-sm font-body-sm text-body-sm font-semibold text-on-surface-variant">
              Cancel
            </button>
            <button type="button" disabled={!!missing || saving} onClick={create} className={`${btnPrimary} px-space-lg py-space-sm`}>
              <span>{saving ? "Creating…" : "Create Pool"}</span>
              <Icon name="arrow_forward" className="text-[18px]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
