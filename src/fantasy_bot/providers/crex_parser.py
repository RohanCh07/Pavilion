"""Pure functions turning CREX (crex.com) pages into domain models.

CREX is an Angular app rendered on the server: every page embeds the data it was built from
as JSON in ``<script id="app-root-state">``. The scraper reads that JSON from three public
pages and never calls CREX's private APIs (robots.txt disallows ``/api/``):

- the home page (``/``): ``getTopMatches`` (formerly ``getLiveMatches``), the live, recent
  and upcoming matches;
- a match's scorecard tab: ``getSC4``, the compact scorecard for every innings;
- a match's info tab: ``getIV4``, the squads, playing XIs, roles and wicketkeepers.

Only raw numbers are read (runs, balls, boundaries, dismissals, overs, wickets...). CREX's own
fantasy points are never used; the scoring engine computes points from the ruleset.

Ids are short base-36 keys ("12JD", "15Q"); they are decoded to ints for the domain and
encoded back for URLs.

Compact scorecard format (``getSC4``, one object per innings, ``c`` = batting team key):

- batting ``b``: ``"PID.runs.balls.4s.6s[.ball.score.how.who...]/..."``; a batter who
  hasn't batted is just ``"PID/..."``; ``how`` is the dismissal code below, ``who`` the
  bowler and/or fielder keys.
- bowling ``a``: ``"PID.runs.balls.maidens.wickets"``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime, timedelta
from typing import Any

from fantasy_bot.domain import (
    CricketPosition,
    CricketStats,
    Fixture,
    FixtureDetails,
    PlayerInfo,
    PlayerLine,
    Series,
    cricket_format,
)

Json = dict[str, Any]

_STATE_RE = re.compile(r'<script id="app-root-state"[^>]*>(.*?)</script>', re.S)
# Angular TransferState escapes; "&a;" must be undone last.
_ESCAPES = (("&q;", '"'), ("&s;", "'"), ("&l;", "<"), ("&g;", ">"), ("&a;", "&"))

# Dismissal codes in the compact scorecard, checked against CREX's rendered scorecards.
BOWLED, CAUGHT, CAUGHT_AND_BOWLED, RUN_OUT, LBW, STUMPED = 1, 2, 3, 4, 5, 8

ROLE_CODES = {
    "1": CricketPosition.BATTER,
    "2": CricketPosition.BOWLER,
    "3": CricketPosition.ALL_ROUNDER,
}

IST = timedelta(hours=5, minutes=30)

# getLiveMatches "s": 0 upcoming, 1 in progress (including breaks and stumps), 2 finished.
STATUS_CODES = {0: "NS", 1: "LIVE", 2: "FT"}


def key_to_id(key: str) -> int:
    return int(key, 36)


def id_to_key(value: int) -> str:
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    out = ""
    while True:
        value, rem = divmod(value, 36)
        out = digits[rem] + out
        if not value:
            return out


def extract_state(html: str) -> Json:
    """The JSON a CREX page was rendered from, keyed by the API URL each part came from."""
    match = _STATE_RE.search(html)
    if not match:
        raise ValueError("CREX page has no app-root-state (layout changed?)")
    body = match.group(1)
    for escaped, char in _ESCAPES:
        body = body.replace(escaped, char)
    return json.loads(body)


def _part(state: Json, marker: str, default: Any = None) -> Any:
    """The state entry whose source URL contains ``marker`` (e.g. "getSC4")."""
    return next((v for k, v in state.items() if marker in k), default)


@dataclass(slots=True)
class Names:
    """Key -> display name lookups merged from every ``getHomeMapData*`` block on a page."""

    players: dict[str, str] = field(default_factory=dict)
    teams: dict[str, str] = field(default_factory=dict)
    team_short: dict[str, str] = field(default_factory=dict)
    series: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_state(cls, state: Json) -> Names:
        names = cls()
        for key, block in state.items():
            if "getHomeMapData" not in key or not isinstance(block, dict):
                continue
            names.players.update({p["f_key"]: p["n"] for p in block.get("p") or []})
            for t in block.get("t") or []:
                names.teams[t["f_key"]] = t["n"]
                names.team_short[t["f_key"]] = t.get("sn") or t["n"]
            names.series.update({s["f_key"]: s["n"] for s in block.get("s") or []})
        return names


def _score(raw: str | None) -> str:
    """ "180/5(20.0" -> "180/5 (20.0)"; CREX leaves the bracket open and may prefix flags."""
    if not raw:
        return ""
    raw = raw.lstrip("!^&")
    runs, _, overs = raw.partition("(")
    return f"{runs} ({overs.rstrip(')')})" if overs else runs


def _scores(
    short: Mapping[str, str], t1: str, t2: str, s1: str, s2: str, result: str
) -> dict[str, str]:
    """Fixture score fields: the one-line text plus each side's score and the result."""
    text = _score_text(short, t1, t2, s1, s2, result)
    return {"score_text": text, "home_score": s1, "away_score": s2, "result": result}


def _score_text(short: Mapping[str, str], t1: str, t2: str, s1: str, s2: str, result: str) -> str:
    a, b = short.get(t1, t1), short.get(t2, t2)
    if not (s1 or s2):
        text = f"{a} vs {b}"
    else:
        text = " · ".join(f"{name} {score}" for name, score in ((a, s1), (b, s2)) if score)
    return f"{text} · {result}" if result else text


def _kickoff(value: Any) -> datetime | None:
    if isinstance(value, int | float) or (isinstance(value, str) and value.isdigit()):
        return datetime.fromtimestamp(int(value) / 1000, UTC)
    if isinstance(value, str) and "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None  # countdown strings like "01h : 55m"


# Home page --------------------------------------------------------------------------------


def _home_matches(state: Json) -> Json:
    """The home page's match list. CREX renamed it from getLiveMatches to getTopMatches
    (several API versions on one page); take the most detailed one present."""
    lists = [
        v
        for k, v in state.items()
        if isinstance(v, dict) and ("getLiveMatches" in k or "getTopMatches" in k)
    ]
    return max(lists, key=lambda v: len(json.dumps(v)), default={})


def map_schedule(state: Json) -> list[Fixture]:
    """Every match on the home page (live, recently finished and upcoming)."""
    names = Names.from_state(state)
    out = []
    for key, m in _home_matches(state).items():
        kickoff = _kickoff(m.get("tiMs")) or _kickoff(m.get("ti"))
        if kickoff is None or not m.get("b") or not m.get("c"):
            continue
        status = STATUS_CODES.get(m.get("s"), "NS")
        t1, t2 = m["b"], m["c"]
        result = (m.get("res") or "") if status == "FT" else ""
        out.append(
            Fixture(
                id=key_to_id(m.get("f_key") or key),
                league_id=key_to_id(m["q"]) if m.get("q") else 0,
                league_name=m.get("sfullname") or names.series.get(m.get("q", ""), ""),
                home_id=key_to_id(t1),
                home_name=names.teams.get(t1) or m.get("team1") or t1,
                away_id=key_to_id(t2),
                away_name=names.teams.get(t2) or m.get("team2") or t2,
                kickoff=kickoff,
                status=status,
                format=cricket_format(m.get("fo") or m.get("format") or m.get("t")),
                **_scores(names.team_short, t1, t2, _score(m.get("j")), _score(m.get("k")), result),
            )
        )
    return out


# Match info tab (squads) ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Squads:
    players: tuple[PlayerInfo, ...]
    playing_xi: frozenset[int]  # empty until the toss

    def position_of(self, player_id: int) -> CricketPosition | None:
        return next((p.position for p in self.players if p.id == player_id), None)


def map_squads(state: Json) -> Squads | None:
    """Both squads with roles, from a match's info tab. None if the page has no squads yet."""
    info = _part(state, "getIV4")
    if not info or not info.get("t"):
        return None
    names = Names.from_state(state)
    team_keys = info["t"].split("-")
    keepers = set((info.get("x") or "").split("/")[1::2])  # "capt1/wk1/capt2/wk2"

    def entries(blob: str | None) -> list[list[list[str]]]:
        teams = (blob or "").split("/")
        return [[e.split(".") for e in t.split("-") if e] for t in teams]

    xi, bench = entries(info.get("tp")), entries(info.get("tb"))
    players: dict[int, PlayerInfo] = {}
    playing: set[int] = set()
    for group, in_xi in ((xi, True), (bench, False)):
        for team_key, team_entries in zip(team_keys, group, strict=False):
            for e in team_entries:
                pid = key_to_id(e[0])
                pos = (
                    CricketPosition.WICKET_KEEPER
                    if e[0] in keepers
                    else ROLE_CODES.get(e[2] if len(e) > 2 else "", CricketPosition.BATTER)
                )
                players.setdefault(
                    pid,
                    PlayerInfo(
                        pid,
                        names.players.get(e[0], e[0]),
                        key_to_id(team_key),
                        names.teams.get(team_key, team_key),
                        pos,
                    ),
                )
                if in_xi:
                    playing.add(pid)
    return Squads(tuple(players.values()), frozenset(playing))


# Scorecard tab ----------------------------------------------------------------------------


@dataclass(slots=True)
class _Tally:
    """Mutable CricketStats accumulator (a player can bat, bowl and field in two innings)."""

    team: str
    in_xi: bool = False
    batted: bool = False
    out: bool = False
    runs: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    balls_bowled: int = 0
    runs_conceded: int = 0
    wickets: int = 0
    lbw_bowled: int = 0
    maidens: int = 0
    catches: int = 0
    stumpings: int = 0
    run_outs_direct: int = 0
    run_outs_assisted: int = 0

    def stats(self) -> CricketStats:
        return CricketStats(**{f.name: getattr(self, f.name) for f in fields(CricketStats)})


def _int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def _innings_scores(innings: list[Json]) -> dict[str, str]:
    """Team key -> "113/10 (39.3)", with " & " between a team's innings in longer formats.

    Taken from the scorecard itself: getSV3's j/k scores are in batting order, which the page
    doesn't state reliably.
    """
    out: dict[str, list[str]] = {}
    for inn in innings:
        total, _, balls = (inn.get("d") or "").partition("(")
        if not total:
            continue
        overs = f" ({_overs(_int(balls))})" if balls else ""
        out.setdefault(inn.get("c", ""), []).append(total + overs)
    return {team: " & ".join(parts) for team, parts in out.items()}


def _overs(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def _fixture_header(state: Json, key: str, names: Names) -> Fixture:
    meta = _part(state, f"match-{key}") or {}
    t1 = (meta.get("team1") or {}).get("fkey", "")
    t2 = (meta.get("team2") or {}).get("fkey", "")
    sv = _part(state, "getSV3") or {}
    scores = _innings_scores(_part(state, "getSC4") or [])
    status = STATUS_CODES.get(meta.get("s"), "NS")
    result = (sv.get("B") or "").replace("🏆", "").strip() if status == "FT" else ""
    series = meta.get("sf", "")
    return Fixture(
        id=key_to_id(key),
        league_id=key_to_id(series) if series else 0,
        league_name=names.series.get(series, ""),
        home_id=key_to_id(t1),
        home_name=(meta.get("team1") or {}).get("name") or names.teams.get(t1, t1),
        away_id=key_to_id(t2),
        away_name=(meta.get("team2") or {}).get("name") or names.teams.get(t2, t2),
        # The match header's "t" is India time labelled as UTC; the provider prefers the
        # home page's kickoff when it has the match.
        kickoff=(_kickoff(meta.get("t")) or datetime.now(UTC) + IST) - IST,
        status=status,
        format=cricket_format(sv.get("fo") or meta.get("ft")),
        **_scores(names.team_short, t1, t2, scores.get(t1, ""), scores.get(t2, ""), result),
    )


def _credit_dismissal(
    tally: Callable[[str, str], _Tally], code: int, who: list[str], fielding_team: str
) -> None:
    """Credit the fielding side for a dismissal. Wickets themselves come from bowling figures."""

    def get(k: str) -> _Tally:
        return tally(k, fielding_team)

    who = [k for k in who if k]
    if code in (BOWLED, LBW) and who:
        get(who[0]).lbw_bowled += 1
    elif code == CAUGHT and len(who) > 1:
        get(who[1]).catches += 1
    elif code == CAUGHT_AND_BOWLED and who:
        get(who[0]).catches += 1
    elif code == STUMPED and len(who) > 1:
        get(who[1]).stumpings += 1
    elif code == RUN_OUT and who:
        if len(who) == 1:
            get(who[0]).run_outs_direct += 1
        else:
            for k in who[-2:]:  # the last two fielders involved
                get(k).run_outs_assisted += 1


def map_scorecard(state: Json, key: str, squads: Squads | None = None) -> FixtureDetails:
    """Per-player raw stats for one match, from its scorecard tab (plus squads if known)."""
    names = Names.from_state(state)
    fixture = _fixture_header(state, key, names)
    teams = {id_to_key(fixture.home_id), id_to_key(fixture.away_id)}
    tallies: dict[str, _Tally] = {}

    def tally(pkey: str, team: str) -> _Tally:
        if pkey not in tallies:
            tallies[pkey] = _Tally(team)
        return tallies[pkey]

    for innings in _part(state, "getSC4") or []:
        batting = innings.get("c", "")
        fielding = next(iter(teams - {batting}), "")
        for entry in innings.get("b") or []:
            head = entry.split("/")[0].split(".")
            t = tally(head[0], batting)
            t.in_xi = True
            if len(head) < 5:
                continue  # yet to bat
            t.batted = True
            t.runs += _int(head[1])
            t.balls_faced += _int(head[2])
            t.fours += _int(head[3])
            t.sixes += _int(head[4])
            if len(head) > 7 and head[7]:
                t.out = True
                _credit_dismissal(tally, _int(head[7]), head[8:], fielding)
        for entry in innings.get("a") or []:
            parts = entry.split(".")
            if len(parts) < 5:
                continue
            t = tally(parts[0], fielding)
            t.in_xi = True
            t.runs_conceded += _int(parts[1])
            t.balls_bowled += _int(parts[2])
            t.maidens += _int(parts[3])
            t.wickets += _int(parts[4])

    known: dict[int, PlayerInfo] = {p.id: p for p in squads.players} if squads else {}
    if squads:  # players named in the XI before they've batted, bowled or fielded
        for pid in squads.playing_xi - {key_to_id(k) for k in tallies}:
            p = known[pid]
            tallies[id_to_key(pid)] = _Tally(id_to_key(p.team_id), in_xi=True)

    lines = []
    for pkey, t in tallies.items():
        pid = key_to_id(pkey)
        info = known.get(pid) or PlayerInfo(
            pid,
            names.players.get(pkey, pkey),
            key_to_id(t.team) if t.team else 0,
            names.teams.get(t.team, t.team),
            CricketPosition.WICKET_KEEPER if t.stumpings else CricketPosition.BATTER,
        )
        if squads and pid in squads.playing_xi:
            t.in_xi = True
        lines.append(PlayerLine(info, t.stats()))
    return FixtureDetails(fixture, tuple(lines))


# Series pages ----------------------------------------------------------------------------

SERIES_STATUS = {1: "live", 2: "finished"}


def map_series_list(state: Json) -> list[Series]:
    """Current series from ``/series`` (``getHomeSeries``)."""
    names = Names.from_state(state)
    out = []
    for s in _part(state, "getHomeSeries") or []:
        key = s.get("sf")
        if not key:
            continue
        out.append(
            Series(
                id=key_to_id(key),
                name=names.series.get(key) or s.get("tn") or key,
                short_name=s.get("tn") or "",
                start=_kickoff(s.get("sd")),
                end=_kickoff(s.get("ed")),
                status=SERIES_STATUS.get(s.get("sst"), "upcoming"),
            )
        )
    return out


def map_series_matches(state: Json) -> list[Fixture]:
    """Every match of a series, from its ``/matches`` tab (``getMatchesForSeriesID``)."""
    names = Names.from_state(state)
    out = []
    for m in _part(state, "getMatchesForSeriesID") or []:
        # Matches far ahead carry their key as "nf" instead of "mf".
        t1, t2, key = m.get("t1f"), m.get("t2f"), m.get("mf") or m.get("nf")
        kickoff = _kickoff(m.get("t"))
        if not (t1 and t2 and key and kickoff):
            continue
        status = STATUS_CODES.get(m.get("status"), "NS")
        first = m.get("bf") or t1
        second = t2 if first == t1 else t1
        scores = {
            first: _score(f"{m['s1']}({m.get('o1', '')}") if m.get("s1") else "",
            second: _score(f"{m['s2']}({m.get('o2', '')}") if m.get("s2") else "",
        }
        result = (m.get("result") or "") if status == "FT" else ""
        out.append(
            Fixture(
                id=key_to_id(key),
                league_id=key_to_id(m["sf"]) if m.get("sf") else 0,
                league_name=names.series.get(m.get("sf", ""), ""),
                home_id=key_to_id(t1),
                home_name=names.teams.get(t1, t1),
                away_id=key_to_id(t2),
                away_name=names.teams.get(t2, t2),
                kickoff=kickoff,
                status=status,
                format=cricket_format(m.get("fo") or m.get("ft")),
                **_scores(names.team_short, t1, t2, scores[t1], scores[t2], result),
            )
        )
    return sorted(out, key=lambda f: f.kickoff)


def map_series_squads(state: Json) -> list[PlayerInfo]:
    """Every team's squad for a series (all formats), from the series overview page."""
    overview = (_part(state, "getSeriesOverview") or {}).get("i1") or {}
    names = Names.from_state(state)
    players: dict[int, PlayerInfo] = {}
    keepers = {k.split("/")[0] for squad in overview.get("s") or [] for k in squad.get("iw") or []}
    for squad in overview.get("s") or []:
        team = squad.get("tf", "")
        for entry in squad.get("pf") or []:
            pkey, _, rest = entry.partition("/")
            if not pkey or pkey == "null" or not team:
                continue
            pos = (
                CricketPosition.WICKET_KEEPER
                if pkey in keepers
                else ROLE_CODES.get(rest.split("/")[0], CricketPosition.BATTER)
            )
            pid = key_to_id(pkey)
            players.setdefault(
                pid,
                PlayerInfo(
                    pid,
                    names.players.get(pkey, pkey),
                    key_to_id(team),
                    names.teams.get(team, team),
                    pos,
                ),
            )
    return list(players.values())
