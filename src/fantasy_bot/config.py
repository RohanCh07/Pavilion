"""Typed settings loaded once from the environment (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


# Data provider -> the sport it serves, and the ruleset used when SCORING_RULESET is unset.
PROVIDER_SPORTS = {
    "api_football": "football",
    "mock": "football",
    "crex": "cricket",
    "mock_cricket": "cricket",
}
DEFAULT_RULESETS = {"football": "dream11_football", "cricket": "dream11_cricket"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def async_database_url(url: str) -> str:
    """Hosts hand out plain Postgres URLs (postgres://...); the app needs the asyncpg driver."""
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix) :]
    return url


def current_season(today: date | None = None) -> int:
    """European seasons run Aug-May and are named by their starting year."""
    today = today or date.today()
    return today.year if today.month >= 8 else today.year - 1


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_token: str
    data_provider: str
    api_football_key: str
    league_ids: tuple[int, ...]
    crex_series: tuple[str, ...]
    season: int
    live_poll_seconds: int
    schedule_refresh_seconds: int
    scoring_ruleset: str
    squad_size: int
    database_url: str
    log_level: str
    # Web API (python -m fantasy_bot.api)
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://localhost:5173")
    team_min_players: int = 1
    team_max_players: int = 11
    web_dist: str = ""  # built front end to serve; empty means web/dist in the project

    @property
    def sport(self) -> str:
        return PROVIDER_SPORTS.get(self.data_provider, "football")

    @classmethod
    def from_env(
        cls, env_file: str | Path | None = ".env", *, require_telegram: bool = True
    ) -> Settings:
        """Read settings; the web API passes ``require_telegram=False``."""
        if env_file:
            load_dotenv(env_file)

        provider = os.getenv("DATA_PROVIDER", "api_football").strip().lower()
        # FOOTBALL_API_KEY is accepted for compatibility with the earlier bot's .env.
        api_key = (os.getenv("API_FOOTBALL_KEY") or os.getenv("FOOTBALL_API_KEY") or "").strip()
        leagues = tuple(
            int(x) for x in os.getenv("LEAGUE_IDS", "39").replace(" ", "").split(",") if x
        )
        series = tuple(
            x.upper() for x in os.getenv("CREX_SERIES", "").replace(" ", "").split(",") if x
        )
        sport = PROVIDER_SPORTS.get(provider, "football")

        settings = cls(
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            data_provider=provider,
            api_football_key=api_key,
            league_ids=leagues,
            crex_series=series,
            season=_int("SEASON", current_season()),
            live_poll_seconds=max(30, _int("LIVE_POLL_SECONDS", 120)),
            schedule_refresh_seconds=max(600, _int("SCHEDULE_REFRESH_SECONDS", 3 * 3600)),
            scoring_ruleset=os.getenv("SCORING_RULESET", "").strip() or DEFAULT_RULESETS[sport],
            squad_size=_int("SQUAD_SIZE", 11),
            database_url=async_database_url(
                os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/fantasy.db")
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            # Hosting platforms (Render, Railway, Fly...) set PORT and expect 0.0.0.0.
            api_host=os.getenv("API_HOST", "0.0.0.0" if os.getenv("PORT") else "127.0.0.1").strip(),
            api_port=_int("API_PORT", _int("PORT", 8000)),
            api_cors_origins=tuple(
                x.strip()
                for x in os.getenv(
                    "API_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
                ).split(",")
                if x.strip()
            ),
            team_min_players=max(1, _int("TEAM_MIN_PLAYERS", 1)),
            team_max_players=_int("TEAM_MAX_PLAYERS", 11),
            web_dist=os.getenv("WEB_DIST", "").strip(),
        )
        settings.validate(require_telegram=require_telegram)
        return settings

    def validate(self, require_telegram: bool = True) -> None:
        if require_telegram and not self.telegram_token:
            raise ConfigError("TELEGRAM_BOT_TOKEN is required (get one from @BotFather).")
        if self.data_provider not in PROVIDER_SPORTS:
            raise ConfigError(f"DATA_PROVIDER must be one of: {', '.join(PROVIDER_SPORTS)}.")
        if self.data_provider == "api_football":
            if not self.api_football_key:
                raise ConfigError("API_FOOTBALL_KEY is required when DATA_PROVIDER=api_football.")
            if not self.league_ids:
                raise ConfigError("LEAGUE_IDS must list at least one league id.")
        if any(not x.isalnum() for x in self.crex_series):
            raise ConfigError("CREX_SERIES must be series keys like 2GR, comma-separated.")
        if self.team_max_players < self.team_min_players:
            raise ConfigError("TEAM_MAX_PLAYERS must be at least TEAM_MIN_PLAYERS.")

    def check_ruleset(self) -> None:
        """Fail early if the scoring ruleset is for a different sport than the provider."""
        from fantasy_bot.scoring import load_rules

        try:
            rules = load_rules(self.scoring_ruleset)
        except (OSError, ValueError, KeyError) as exc:
            raise ConfigError(f"SCORING_RULESET {self.scoring_ruleset!r}: {exc}") from exc
        if rules.sport != self.sport:
            raise ConfigError(
                f"SCORING_RULESET {self.scoring_ruleset!r} is a {rules.sport} ruleset, but "
                f"DATA_PROVIDER={self.data_provider} serves {self.sport}."
            )
