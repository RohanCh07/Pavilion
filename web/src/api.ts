// Typed client for the Python API (see docs/API.md). Shapes mirror src/fantasy_bot/api/schemas.py.

export type Role = "player" | "captain" | "vice_captain";
export type Position = "batter" | "wicket_keeper" | "all_rounder" | "bowler";
export type MatchStatus = "NS" | "LIVE" | "FT";

export interface Series {
  id: number;
  name: string;
  short_name: string;
  start: string | null;
  end: string | null;
  status: "upcoming" | "live" | "finished";
}

export interface Side {
  id: number;
  name: string;
  score: string;
}

export interface Match {
  id: number;
  series_id: number;
  series_name: string;
  home: Side;
  away: Side;
  start: string;
  status: MatchStatus;
  format: "t20" | "odi" | "test" | "";
  score: string;
  result: string;
}

export interface Player {
  id: number;
  name: string;
  team_id: number;
  team_name: string;
  position: Position;
}

export interface Pick extends Player {
  role: Role;
}

export interface Team {
  id: number;
  owner: string;
  name: string;
  series_id: number;
  series_name: string;
  match_id: number | null;
  pool_id: number | null;
  players: Pick[];
  created_at: string | null;
  updated_at: string | null;
}

export interface Line {
  key: string;
  label: string;
  count: number;
  points: number;
}

export interface Points {
  base: number;
  multiplier: number;
  points: number;
  lines: Line[];
}

export interface PlayerScore extends Points {
  player_id: number;
  name: string;
  role: Role;
  played: boolean;
}

export interface MatchScore {
  match: Match;
  points: number;
  players: PlayerScore[];
}

export interface TeamScore {
  team: Team;
  points: number;
  players: { player_id: number; name: string; role: Role; points: number }[];
  matches: MatchScore[];
}

export interface LeaderboardRow {
  rank: number;
  team_id: number;
  team_name: string;
  owner: string;
  points: number;
  matches_scored: number;
}

export interface ScorecardPlayer extends Points {
  player: Player;
  stats: Record<string, number | boolean>;
}

export interface Scorecard {
  match: Match;
  players: ScorecardPlayer[];
}

export interface Rules {
  sport: string;
  name: string;
  version: string;
  captain: number;
  vice_captain: number;
  team_min_players: number;
  team_max_players: number;
  sections: { title: string; items: string[] }[];
  formats: { format: string; name: string; sections: { title: string; items: string[] }[] }[];
}

export type PoolKind = "normal" | "dream";

export interface Pool {
  id: number;
  owner: string;
  name: string;
  type: PoolKind;
  series_id: number;
  series_name: string;
  match_id: number | null;
  team_count: number;
  created_at: string | null;
}

export interface PoolStanding {
  rank: number;
  team: Team;
  points: number;
  matches_scored: number;
  captain: string | null;
  vice_captain: string | null;
}

export interface PoolDetail {
  pool: Pool;
  leaderboard: PoolStanding[];
}

export interface PoolTeamIn {
  name: string;
  players: PickIn[];
}

export interface PickIn {
  player_id: number;
  role: Role;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// The user is whoever this browser says it is (see user.ts); real login comes later.
let userId = "";
export function setApiUser(id: string) {
  userId = id;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (userId) headers["X-User-Id"] = userId;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let resp: Response;
  try {
    resp = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "You're offline or the server can't be reached.");
  }
  if (resp.status === 204) return undefined as T;
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join(", ")
          : `Request failed (${resp.status})`;
    throw new ApiError(resp.status, message);
  }
  return data as T;
}

// Small in-memory cache so moving between screens feels instant; callers can force a refresh.
const cache = new Map<string, { at: number; data: unknown }>();
const TTL_MS = 30_000;

export async function get<T>(path: string, fresh = false): Promise<T> {
  const hit = cache.get(path);
  if (!fresh && hit && Date.now() - hit.at < TTL_MS) return hit.data as T;
  const data = await request<T>("GET", path);
  cache.set(path, { at: Date.now(), data });
  return data;
}

export function clearCache() {
  cache.clear();
}

export function peek<T>(path: string): T | undefined {
  return cache.get(path)?.data as T | undefined;
}

function invalidateTeams() {
  for (const key of cache.keys())
    if (key.startsWith("/api/teams") || key.startsWith("/api/pools") || key.includes("/leaderboard"))
      cache.delete(key);
}

export const api = {
  rules: () => get<Rules>("/api/rules"),
  series: () => get<Series[]>("/api/series"),
  currentMatches: (fresh = false) => get<Match[]>("/api/matches", fresh),
  matches: (seriesId: number, fresh = false) =>
    get<Match[]>(`/api/series/${seriesId}/matches`, fresh),
  players: (seriesId: number, matchId?: number | null) =>
    get<Player[]>(`/api/series/${seriesId}/players${matchId ? `?match_id=${matchId}` : ""}`),
  scorecard: (seriesId: number, matchId: number, fresh = false) =>
    get<Scorecard>(`/api/series/${seriesId}/matches/${matchId}/scorecard`, fresh),
  leaderboard: (seriesId: number, fresh = false) =>
    get<LeaderboardRow[]>(`/api/series/${seriesId}/leaderboard`, fresh),
  myTeams: (fresh = false) => get<Team[]>("/api/teams", fresh),
  team: (id: number) => get<Team>(`/api/teams/${id}`),
  score: (id: number, fresh = false) => get<TeamScore>(`/api/teams/${id}/score`, fresh),

  async createTeam(body: {
    name: string;
    series_id: number;
    match_id: number | null;
    players: PickIn[];
  }) {
    const team = await request<Team>("POST", "/api/teams", body);
    invalidateTeams();
    return team;
  },
  async editTeam(id: number, body: { name?: string; players?: PickIn[] }) {
    const team = await request<Team>("PATCH", `/api/teams/${id}`, body);
    invalidateTeams();
    return team;
  },
  async deleteTeam(id: number) {
    await request<void>("DELETE", `/api/teams/${id}`);
    invalidateTeams();
  },

  myPools: (fresh = false) => get<Pool[]>("/api/pools", fresh),
  pool: (id: number, fresh = false) => get<PoolDetail>(`/api/pools/${id}`, fresh),
  async createPool(body: {
    name: string;
    type: PoolKind;
    series_id: number;
    match_id: number | null;
    teams: PoolTeamIn[];
  }) {
    const pool = await request<PoolDetail>("POST", "/api/pools", body);
    invalidateTeams();
    return pool;
  },
  async addPoolTeam(poolId: number, body: PoolTeamIn) {
    const team = await request<Team>("POST", `/api/pools/${poolId}/teams`, body);
    invalidateTeams();
    return team;
  },
  async renamePool(poolId: number, name: string) {
    const pool = await request<Pool>("PATCH", `/api/pools/${poolId}`, { name });
    invalidateTeams();
    return pool;
  },
  async deletePool(poolId: number) {
    await request<void>("DELETE", `/api/pools/${poolId}`);
    invalidateTeams();
  },
};
