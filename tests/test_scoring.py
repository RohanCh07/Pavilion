import pytest

from fantasy_bot.domain import PlayerStats, Position, Role
from fantasy_bot.scoring import ScoringRules, calculate_points


def total(rules, position=Position.FORWARD, role=Role.PLAYER, **stats):
    return calculate_points(PlayerStats(**stats), position, rules, role).total


def test_unused_player_scores_nothing(rules):
    result = calculate_points(PlayerStats(), Position.FORWARD, rules)
    assert result.lines == () and result.total == 0


def test_starter_vs_substitute(rules):
    assert total(rules, minutes=90, started=True, team_conceded=1) == 4
    assert total(rules, minutes=20, started=False, team_conceded=1) == 2


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        (Position.GOALKEEPER, 12),
        (Position.DEFENDER, 10),
        (Position.MIDFIELDER, 8),
        (Position.FORWARD, 6),
    ],
)
def test_goal_points_depend_on_position(rules, position, expected):
    # 10 minutes off the bench, team conceded, so no clean sheet muddies the sum.
    assert total(rules, position, minutes=10, goals=1, team_conceded=2) == 2 + expected


def test_clean_sheet_needs_minimum_minutes(rules):
    assert total(rules, Position.DEFENDER, minutes=59, started=True) == 4
    assert total(rules, Position.DEFENDER, minutes=60, started=True) == 4 + 8
    assert total(rules, Position.FORWARD, minutes=90, started=True) == 4  # forwards get none


def test_goalkeeper_saves_and_penalty_save(rules):
    pts = total(
        rules,
        Position.GOALKEEPER,
        minutes=90,
        started=True,
        saves=3,
        penalties_saved=1,
        team_conceded=1,
    )
    assert pts == 4 + 3 * 2 + 12


def test_saves_ignored_for_outfield_players(rules):
    assert total(rules, Position.DEFENDER, minutes=90, started=True, saves=2, team_conceded=1) == 4


def test_red_card_replaces_yellow(rules):
    assert (
        total(rules, minutes=90, started=True, yellow_cards=1, red_cards=1, team_conceded=1)
        == 4 - 4
    )


def test_negative_events(rules):
    assert (
        total(rules, minutes=90, started=True, own_goals=1, penalties_missed=1, team_conceded=1)
        == 4 - 6 - 4
    )


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (Role.PLAYER, 18),
        (Role.CAPTAIN, 36),
        (Role.VICE_CAPTAIN, 27),
    ],
)
def test_role_multipliers(rules, role, expected):
    # starter 4 + goal 6 + assist 8 = 18
    assert (
        total(rules, role=role, minutes=90, started=True, goals=1, assists=1, team_conceded=1)
        == expected
    )


def test_custom_ruleset_defaults_and_overrides():
    rules = ScoringRules.from_mapping(
        {
            "appearance": {"starting_xi": 1},
            "per_event": {"goals": {"default": 5, "defender": 9}},
        }
    )
    assert total(rules, Position.DEFENDER, minutes=90, started=True, goals=1, team_conceded=1) == 10
    assert total(rules, Position.FORWARD, minutes=90, started=True, goals=1, team_conceded=1) == 6


def test_unknown_position_key_is_rejected():
    with pytest.raises(ValueError, match="Unknown position"):
        ScoringRules.from_mapping({"per_event": {"goals": {"striker": 5}}})
