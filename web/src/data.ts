// Shared loaders used by several screens.
import { api, type LeaderboardRow, type Team, type TeamScore } from "./api";
import { useData } from "./hooks";
import { useUser } from "./user";

/** The user's teams and each team's score (scores load after the list). */
export function useMyTeams() {
  const user = useUser();
  const teams = useData((fresh) => api.myTeams(fresh), [user]);
  const ids = (teams.data ?? []).map((t) => t.id).join(",");
  const scores = useData(
    () =>
      Promise.all(
        (teams.data ?? []).map((t) =>
          api
            .score(t.id)
            .then((s) => [t.id, s] as const)
            .catch(() => [t.id, null] as const),
        ),
      ).then((pairs) => new Map<number, TeamScore | null>(pairs)),
    [ids],
  );
  return { teams, scores: scores.data ?? new Map<number, TeamScore | null>(), scoresLoading: scores.loading };
}

/** Rank of each of ``teams`` in its series leaderboard (series teams only). */
export function useRanks(teams: Team[]) {
  const seriesIds = [...new Set(teams.filter((t) => t.match_id === null).map((t) => t.series_id))];
  const boards = useData(
    () =>
      Promise.all(seriesIds.map((id) => api.leaderboard(id).then((b) => [id, b] as const).catch(() => [id, [] as LeaderboardRow[]] as const))).then(
        (pairs) => new Map<number, LeaderboardRow[]>(pairs),
      ),
    [seriesIds.join(",")],
  );
  const map = boards.data ?? new Map<number, LeaderboardRow[]>();
  return (team: Team): { rank: number; of: number } | null => {
    const board = map.get(team.series_id);
    const row = board?.find((r) => r.team_id === team.id);
    return row && board ? { rank: row.rank, of: board.length } : null;
  };
}
