// Rankings: the series leaderboard widget from the design, one per series you play.
import { api } from "../api";
import { Icon } from "../components/Icon";
import { btnPrimary, EmptyPanel, ErrorBox, Skeletons } from "../components/ui";
import { navigate, useData } from "../hooks";
import { useUser } from "../user";
import { LeaderboardRows } from "./SeriesPage";

function Board({ seriesId, name }: { seriesId: number; name: string }) {
  const user = useUser();
  const board = useData((fresh) => api.leaderboard(seriesId, fresh), [seriesId]);
  const rows = board.data ?? [];
  const me = rows.find((r) => r.owner === user);
  return (
    <div className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
      <div className="flex items-center justify-between gap-space-sm pb-space-2xs">
        <div className="flex min-w-0 items-center gap-space-xs">
          <Icon name="emoji_events" className="text-[20px] text-primary" />
          <h2 className="truncate font-headline-md text-[18px] font-bold text-on-surface">{name}</h2>
        </div>
        <button
          type="button"
          onClick={() => navigate(`/series/${seriesId}?tab=leaderboard`)}
          className="shrink-0 font-label-meta text-label-meta font-semibold text-primary hover:underline"
        >
          View All ({rows.length})
        </button>
      </div>
      {board.loading && !board.data ? (
        <div className="skeleton h-40" />
      ) : (
        <LeaderboardRows rows={rows.slice(0, 5)} user={user} />
      )}
      {me && me.rank > 5 && (
        <>
          <div className="text-center font-label-meta text-label-meta text-outline">…</div>
          <LeaderboardRows rows={[me]} user={user} />
        </>
      )}
    </div>
  );
}

export function Leaderboards() {
  const user = useUser();
  const teams = useData(() => api.myTeams(), [user]);
  const series = new Map<number, string>();
  for (const t of teams.data ?? []) if (t.match_id === null) series.set(t.series_id, t.series_name);

  return (
    <div className="flex w-full flex-col">
      <div className="mb-space-xl flex flex-col">
        <div className="mb-space-2xs flex items-center gap-space-xs text-outline">
          <span className="font-label-meta text-label-meta font-semibold tracking-wider uppercase">Pavilion Rankings</span>
        </div>
        <h1 className="font-headline-xl-mobile text-headline-xl-mobile tracking-tight text-on-surface md:font-headline-xl md:text-headline-xl">
          Leaderboards
        </h1>
        <p className="mt-space-2xs max-w-2xl font-body-md text-body-md text-on-surface-variant">
          Series teams ranked by total fantasy points, for every series you've entered.
        </p>
      </div>
      {teams.loading && !teams.data ? (
        <Skeletons rows={2} height={260} />
      ) : teams.error && !teams.data ? (
        <ErrorBox message={teams.error} onRetry={() => teams.reload(true)} />
      ) : series.size === 0 ? (
        <EmptyPanel
          icon="leaderboard"
          title="Nothing to rank yet"
          text="Create a team for a whole series to see how it ranks against everyone else's."
          action={
            <button type="button" onClick={() => navigate("/")} className={`${btnPrimary} px-space-xl py-space-sm`}>
              Browse Series
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-space-lg lg:grid-cols-2">
          {[...series.entries()].map(([id, name]) => (
            <Board key={id} seriesId={id} name={name} />
          ))}
        </div>
      )}
    </div>
  );
}
