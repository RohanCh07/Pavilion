"""The web API for a front end: series, matches, players, fantasy teams and their scores.

Users are identified by the ``X-User-Id`` header for now (any stable string the front end
picks, e.g. a Telegram user id). Put real authentication in front of it before going public.

Interactive docs are served at ``/docs`` while the API runs.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from fantasy_bot.api import schemas as s
from fantasy_bot.config import Settings
from fantasy_bot.domain import Role
from fantasy_bot.fantasy import FantasyService, TeamError, TeamLimits
from fantasy_bot.providers import ProviderError, build_provider, supports_series
from fantasy_bot.scoring import calculate_points, load_rules
from fantasy_bot.storage import TeamRepository, create_engine, init_db, session_factory

log = logging.getLogger(__name__)

# The built front end (cd web && npm run build). Served at / when present.
WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"

ERROR_STATUS = {"not_found": 404, "invalid": 422, "forbidden": 403, "locked": 409}


def _service(request: Request) -> FantasyService:
    return request.app.state.service


def _user(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id or not x_user_id.strip() or len(x_user_id) > 64:
        raise HTTPException(401, "Send an X-User-Id header identifying the user.")
    return x_user_id.strip()


# Module level so FastAPI can resolve them from the (postponed) annotations.
Svc = Annotated[FantasyService, Depends(_service)]
User = Annotated[str, Depends(_user)]


def build_service(settings: Settings, provider=None, sessions=None) -> FantasyService:
    rules = load_rules(settings.scoring_ruleset)
    provider = provider or build_provider(settings)
    if not supports_series(provider):
        raise RuntimeError(
            f"DATA_PROVIDER={settings.data_provider} has no series support; "
            "use crex or mock_cricket for the web API."
        )
    limits = TeamLimits(settings.team_min_players, settings.team_max_players)
    return FantasyService(provider, TeamRepository(sessions, rules.stats_type), rules, limits)


def create_app(settings: Settings, service: FantasyService | None = None) -> FastAPI:
    """Build the API. Tests pass a ready ``service``; otherwise it's built on startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if service is not None:
            app.state.service = service
            yield
            return
        engine = create_engine(settings.database_url)
        await init_db(engine)
        app.state.service = build_service(settings, sessions=session_factory(engine))
        try:
            yield
        finally:
            await app.state.service.aclose()
            await engine.dispose()

    app = FastAPI(title="Fantasy Points API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.api_cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(TeamError)
    async def _team_error(_: Request, exc: TeamError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=ERROR_STATUS.get(exc.kind, 400))

    @app.exception_handler(ProviderError)
    async def _provider_error(_: Request, exc: ProviderError) -> JSONResponse:
        log.warning("Provider error: %s", exc)
        return JSONResponse(
            {"detail": "The sports data source isn't answering. Try again shortly."},
            status_code=503,
        )

    # Reference data ----------------------------------------------------------------------

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "sport": settings.sport}

    @app.get("/api/rules")
    async def rules(service: Svc) -> s.RulesOut:
        r = service.rules
        return s.RulesOut(
            sport=r.sport,
            name=r.name,
            version=r.version,
            captain=r.multipliers[Role.CAPTAIN],
            vice_captain=r.multipliers[Role.VICE_CAPTAIN],
            team_min_players=service.limits.min_players,
            team_max_players=service.limits.max_players,
            sections=s.RulesOut.sections_of(r),
            formats=s.RulesOut.formats_of(r),
        )

    @app.get("/api/matches")
    async def current_matches(service: Svc) -> list[s.MatchOut]:
        """Live, recent and upcoming matches across all series (the match centre)."""
        return [s.MatchOut.of(f) for f in await service.current_matches()]

    @app.get("/api/series")
    async def list_series(service: Svc) -> list[s.SeriesOut]:
        return [s.SeriesOut.of(x) for x in await service.list_series()]

    @app.get("/api/series/{series_id}/matches")
    async def series_matches(series_id: int, service: Svc) -> list[s.MatchOut]:
        return [s.MatchOut.of(f) for f in await service.series_matches(series_id)]

    @app.get("/api/series/{series_id}/players")
    async def series_players(
        series_id: int,
        service: Svc,
        match_id: int | None = None,
        q: Annotated[str, Query(max_length=40)] = "",
    ) -> list[s.PlayerOut]:
        """Players a team may pick: the series squads, or the two sides of ``match_id``."""
        return [s.PlayerOut.of(p) for p in await service.players(series_id, match_id, q)]

    @app.get("/api/series/{series_id}/matches/{match_id}/scorecard")
    async def scorecard(series_id: int, match_id: int, service: Svc) -> s.ScorecardOut:
        fixture = await service.match(series_id, match_id)
        details = await service.match_details(fixture, series_id)
        players = []
        for line in details.players if details else ():
            result = calculate_points(
                line.stats, line.player.position, service.rules, fmt=details.fixture.format
            )
            players.append(
                s.ScorecardPlayerOut(
                    **s.PointsOut.of(result).model_dump(),
                    player=s.PlayerOut.of(line.player),
                    stats=line.stats.to_dict(),
                )
            )
        players.sort(key=lambda p: -p.points)
        return s.ScorecardOut(
            match=s.MatchOut.of(details.fixture if details else fixture), players=players
        )

    @app.get("/api/series/{series_id}/leaderboard")
    async def leaderboard(
        series_id: int, service: Svc, match_id: int | None = None
    ) -> list[s.LeaderboardRowOut]:
        """Series teams ranked by points; with ``match_id``, that match's teams instead."""
        rows = await service.leaderboard(series_id, match_id)
        return [
            s.LeaderboardRowOut(
                rank=i,
                team_id=r.team.id,
                team_name=r.team.name,
                owner=r.team.owner,
                points=r.total,
                matches_scored=len(r.matches),
            )
            for i, r in enumerate(rows, start=1)
        ]

    # Teams -------------------------------------------------------------------------------

    @app.get("/api/teams")
    async def my_teams(
        service: Svc, owner: User, series_id: int | None = None, match_id: int | None = None
    ) -> list[s.TeamOut]:
        teams = await service.list_teams(owner, series_id, match_id)
        return [s.TeamOut.of(t) for t in teams]

    @app.post("/api/teams", status_code=201)
    async def create_team(body: s.TeamIn, service: Svc, owner: User) -> s.TeamOut:
        team = await service.create_team(
            owner,
            body.name,
            body.series_id,
            [(p.player_id, p.role) for p in body.players],
            body.match_id,
        )
        return s.TeamOut.of(team)

    @app.get("/api/teams/{team_id}")
    async def get_team(team_id: int, service: Svc) -> s.TeamOut:
        return s.TeamOut.of(await service.get_team(team_id))

    @app.patch("/api/teams/{team_id}")
    async def edit_team(team_id: int, body: s.TeamPatch, service: Svc, owner: User) -> s.TeamOut:
        picks = None if body.players is None else [(p.player_id, p.role) for p in body.players]
        return s.TeamOut.of(await service.update_team(team_id, owner, name=body.name, picks=picks))

    @app.put("/api/teams/{team_id}/role")
    async def set_role(team_id: int, body: s.RoleIn, service: Svc, owner: User) -> s.TeamOut:
        """Make a player captain, vice-captain or a plain pick; the role moves off anyone else."""
        return s.TeamOut.of(await service.set_role(team_id, owner, body.player_id, body.role))

    @app.delete("/api/teams/{team_id}", status_code=204)
    async def delete_team(team_id: int, service: Svc, owner: User) -> Response:
        await service.delete_team(team_id, owner)
        return Response(status_code=204)

    @app.get("/api/teams/{team_id}/score")
    async def team_score(team_id: int, service: Svc) -> s.TeamScoreOut:
        """Points per match and in total, for every match of the series that has started."""
        return s.TeamScoreOut.of(await service.team_score(team_id))

    # Pools -------------------------------------------------------------------------------

    def _detail(pool, scores) -> s.PoolDetailOut:
        def holder(team, role):
            return next((p.player.name for p in team.picks if p.role is role), None)

        return s.PoolDetailOut(
            pool=s.PoolOut.of(pool, len(scores)),
            leaderboard=[
                s.PoolStandingOut(
                    rank=i,
                    team=s.TeamOut.of(sc.team),
                    points=sc.total,
                    matches_scored=len(sc.matches),
                    captain=holder(sc.team, Role.CAPTAIN),
                    vice_captain=holder(sc.team, Role.VICE_CAPTAIN),
                )
                for i, sc in enumerate(scores, start=1)
            ],
        )

    @app.get("/api/pools")
    async def my_pools(service: Svc, owner: User) -> list[s.PoolOut]:
        return [s.PoolOut.of(p, n) for p, n in await service.list_pools(owner)]

    @app.post("/api/pools", status_code=201)
    async def create_pool(body: s.PoolIn, service: Svc, owner: User) -> s.PoolDetailOut:
        """Create a pool with its first teams (a normal pool needs at least one)."""
        pool = await service.create_pool(
            owner,
            body.name,
            body.type,
            body.series_id,
            [(t.name, [(p.player_id, p.role) for p in t.players]) for t in body.teams],
            body.match_id,
        )
        return _detail(*await service.pool_leaderboard(pool.id))

    @app.get("/api/pools/{pool_id}")
    async def get_pool(pool_id: int, service: Svc) -> s.PoolDetailOut:
        """The pool with its teams ranked by points (the pool's leaderboard)."""
        return _detail(*await service.pool_leaderboard(pool_id))

    @app.patch("/api/pools/{pool_id}")
    async def rename_pool(pool_id: int, body: s.PoolPatch, service: Svc, owner: User) -> s.PoolOut:
        pool = await service.rename_pool(pool_id, owner, body.name)
        return s.PoolOut.of(pool, len(await service.pool_teams(pool_id)))

    @app.delete("/api/pools/{pool_id}", status_code=204)
    async def delete_pool(pool_id: int, service: Svc, owner: User) -> Response:
        await service.delete_pool(pool_id, owner)
        return Response(status_code=204)

    @app.post("/api/pools/{pool_id}/teams", status_code=201)
    async def add_pool_team(
        pool_id: int, body: s.PoolTeamIn, service: Svc, owner: User
    ) -> s.TeamOut:
        """Add a team to a pool. Edit or delete it later with the /api/teams endpoints."""
        team = await service.add_pool_team(
            pool_id, owner, body.name, [(p.player_id, p.role) for p in body.players]
        )
        return s.TeamOut.of(team)

    # Mounted last so it never shadows /api routes.
    web_dist = Path(settings.web_dist) if settings.web_dist else WEB_DIST
    if (web_dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    else:
        log.info("No built front end at %s; serving the API only", web_dist)

    return app
