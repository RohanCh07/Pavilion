from fantasy_bot.config import Settings
from fantasy_bot.providers.base import (
    DataProvider,
    FootballProvider,
    ProviderError,
    SeriesProvider,
    supports_series,
)


def build_provider(settings: Settings) -> DataProvider:
    match settings.data_provider:
        case "mock":
            from fantasy_bot.providers.mock import MockProvider

            return MockProvider()
        case "mock_cricket":
            from fantasy_bot.providers.mock_cricket import MockCricketProvider

            return MockCricketProvider()
        case "crex":
            from fantasy_bot.providers.crex import CrexProvider

            return CrexProvider(settings.crex_series)
        case _:
            from fantasy_bot.providers.api_football import ApiFootballProvider

            return ApiFootballProvider(
                settings.api_football_key, settings.league_ids, settings.season
            )


__all__ = [
    "DataProvider",
    "FootballProvider",
    "ProviderError",
    "SeriesProvider",
    "build_provider",
    "supports_series",
]
