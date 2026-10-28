from fantasy_bot import messages
from fantasy_bot.utils.cache import TTLCache


def test_points_formatting():
    assert messages.pts(12) == "12"
    assert messages.pts(13.5) == "13.5"
    assert messages.pts(6, signed=True) == "+6"
    assert messages.pts(-4, signed=True) == "-4"


def test_rules_text_lists_every_rule(rules):
    text = messages.rules_text(rules)
    for fragment in (
        "Starting XI: +4",
        "Assists: +8",
        "Own goals: -6",
        "Clean sheet (60+ min)",
        "Captain ×2",
        "Vice-captain ×1.5",
    ):
        assert fragment in text


def test_player_names_are_html_escaped(rules):
    from fantasy_bot.domain import PlayerInfo, Position

    p = PlayerInfo(1, "<script>", 1, "T", Position.FORWARD)
    assert "&lt;script&gt;" in messages.player_label(p)


def test_ttl_cache_expiry_and_eviction():
    now = [0.0]
    cache = TTLCache(maxsize=2, clock=lambda: now[0])
    cache.set("a", 1, ttl=10)
    cache.set("b", None, ttl=10)
    assert cache.get("b", "miss") is None  # cached None is a hit
    now[0] = 11
    assert cache.get("a") is None
    cache.set("c", 3, ttl=10)
    cache.set("d", 4, ttl=10)
    cache.set("e", 5, ttl=10)
    assert len(cache) == 2 and cache.get("c") is None
