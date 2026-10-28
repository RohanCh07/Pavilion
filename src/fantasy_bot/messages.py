"""User-facing message text (Telegram HTML). Pure functions, so they're easy to test."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from html import escape

from fantasy_bot.domain import CricketPosition, Fixture, PlayerInfo, Position, Role
from fantasy_bot.live.events import PointChange
from fantasy_bot.scoring import CricketRules, PointsResult, Rules, ScoringRules
from fantasy_bot.scoring.cricket import RateRule, Threshold
from fantasy_bot.scoring.engine import STAT_LABELS
from fantasy_bot.storage import SquadMember

POSITION_ICON = {
    Position.GOALKEEPER: "🧤",
    Position.DEFENDER: "🛡️",
    Position.MIDFIELDER: "⚙️",
    Position.FORWARD: "⚡",
    CricketPosition.BATTER: "🏏",
    CricketPosition.WICKET_KEEPER: "🧤",
    CricketPosition.ALL_ROUNDER: "⚖️",
    CricketPosition.BOWLER: "🎳",
}
EXAMPLE_PLAYER = {"football": "saka", "cricket": "tilak"}
ROLE_TAG = {Role.CAPTAIN: " (C)", Role.VICE_CAPTAIN: " (VC)", Role.PLAYER: ""}
EVENT_ICON = {
    "starting_xi": "🟢",
    "substitute": "🔁",
    "goals": "⚽",
    "assists": "🎯",
    "saves": "🧤",
    "penalties_saved": "🧱",
    "penalties_missed": "❌",
    "own_goals": "🙈",
    "yellow_cards": "🟨",
    "red_cards": "🟥",
    "clean_sheet": "🔒",
    # cricket
    "playing_xi": "🟢",
    "runs": "🏏",
    "fours": "4️⃣",
    "sixes": "6️⃣",
    "milestone": "🎉",
    "duck": "🦆",
    "wickets": "🎯",
    "lbw_bowled": "🎯",
    "wicket_haul": "🔥",
    "maidens": "🧱",
    "catches": "🙌",
    "catch_bonus": "🙌",
    "stumpings": "🧤",
    "run_outs_direct": "🏃",
    "run_outs_assisted": "🏃",
}


def pts(value: float, signed: bool = False) -> str:
    text = f"{value:.0f}" if float(value).is_integer() else f"{value:.1f}"
    return f"+{text}" if signed and value > 0 else text


def player_label(p: PlayerInfo, role: Role = Role.PLAYER) -> str:
    return f"{POSITION_ICON[p.position]} <b>{escape(p.name)}</b>{ROLE_TAG[role]}"


def fixture_line(f: Fixture) -> str:
    clock = f" {f.elapsed}'" if f.is_live and f.elapsed else ""
    return f"{escape(f.scoreline)} <i>[{f.status}{clock}]</i>"


EVENT_TEXT = {
    "starting_xi": "is in the starting XI",
    "substitute": "came off the bench",
    "goals": "scored",
    "assists": "got an assist",
    "saves": "made a save",
    "penalties_saved": "saved a penalty",
    "penalties_missed": "missed a penalty",
    "own_goals": "scored an own goal",
    "yellow_cards": "was booked",
    "red_cards": "was sent off",
}
# Cricket stats usually move by more than one per poll, so these say how many.
CRICKET_EVENT_TEXT = {
    "playing_xi": "is in the playing XI",
    "runs": "scored {n} run{s}",
    "fours": "hit {n} four{s}",
    "sixes": "hit {n} six{es}",
    "duck": "was out for a duck",
    "wickets": "took {n} wicket{s}",
    "lbw_bowled": "got the LBW/bowled bonus",
    "maidens": "bowled {n} maiden{s}",
    "catches": "took {n} catch{es}",
    "stumpings": "made {n} stumping{s}",
    "run_outs_direct": "ran a batter out (direct hit)",
    "run_outs_assisted": "helped run a batter out",
}
LABEL_EVENTS = frozenset({"milestone", "wicket_haul", "catch_bonus"})  # "earned the <label>"


def _change_text(c: PointChange) -> str:
    if c.key == "clean_sheet":
        return "kept a clean sheet" if c.points_delta > 0 else "lost the clean sheet"
    if c.key in LABEL_EVENTS:
        return f"earned the {c.label}" if c.points_delta > 0 else f"lost the {c.label}"
    if c.count_delta < 0:  # the data provider took an event back (e.g. goal re-attributed)
        return f"had {c.label.lower()} corrected"
    if template := CRICKET_EVENT_TEXT.get(c.key):
        many = c.count_delta != 1
        return template.format(n=c.count_delta, s="s" if many else "", es="es" if many else "")
    text = EVENT_TEXT.get(c.key, c.label.lower())
    return f"{text} ({c.count_delta}x)" if c.count_delta > 1 else text


def live_update(
    fixture: Fixture, items: Sequence[tuple[SquadMember, PointChange]], rules: Rules
) -> str:
    out = [f"📣 <b>Live</b> · {fixture_line(fixture)}", ""]
    total = 0.0
    for member, change in items:
        mult = rules.multipliers[member.role]
        delta = change.points_delta * mult
        total += delta
        boost = f" (×{pts(mult)})" if mult != 1 else ""
        name = f"<b>{escape(member.player.name)}</b>{ROLE_TAG[member.role]}"
        out.append(
            f"{EVENT_ICON.get(change.key, '•')} {name} {_change_text(change)}: "
            f"<b>{pts(delta, signed=True)}</b>{boost}"
        )
    if len(items) > 1:
        out += ["", f"Net change: <b>{pts(total, signed=True)}</b>"]
    return "\n".join(out)


FINAL_TITLE = {"football": "Full time", "cricket": "Match over"}


def full_time(
    fixture: Fixture, rows: Sequence[tuple[SquadMember, PointsResult]], sport: str = "football"
) -> str:
    out = [f"🏁 <b>{FINAL_TITLE[sport]}</b> · {fixture_line(fixture)}", ""]
    for member, result in rows:
        out.append(f"{player_label(member.player, member.role)}: <b>{pts(result.total)}</b> pts")
    out += ["", f"Your players from this match: <b>{pts(sum(r.total for _, r in rows))}</b> pts"]
    return "\n".join(out)


def breakdown(player: PlayerInfo, fixture: Fixture, result: PointsResult, role: Role) -> str:
    out = [player_label(player, role), escape(player.team_name), fixture_line(fixture), ""]
    if not result.lines:
        out.append("No points yet (didn't play or no scoring events).")
    for line in result.lines:
        count = f" x{line.count}" if line.count > 1 else ""
        out.append(
            f"{EVENT_ICON.get(line.key, '•')} {escape(line.label)}{count}: "
            f"{pts(line.points, signed=True)}"
        )
    out.append("")
    if result.multiplier != 1:
        out.append(
            f"Base {pts(result.base)} × {pts(result.multiplier)} = <b>{pts(result.total)} pts</b>"
        )
    else:
        out.append(f"🏆 <b>{pts(result.total)} pts</b>")
    return "\n".join(out)


def squad(
    rows: Sequence[tuple[SquadMember, PointsResult | None, str]],
    max_size: int,
    example: str = "saka",
) -> str:
    if not rows:
        return (
            f"Your squad is empty.\nAdd players with <code>/add {example}</code>, "
            "then I'll send you live points while they play."
        )
    out = [f"👥 <b>Your squad</b> ({len(rows)}/{max_size})", ""]
    total = 0.0
    for member, result, label in rows:
        if result is None:
            out.append(f"{player_label(member.player, member.role)} · no match yet")
            continue
        total += result.total
        out.append(
            f"{player_label(member.player, member.role)} · <b>{pts(result.total)}</b> "
            f"<i>({escape(label)})</i>"
        )
    out += [
        "",
        f"Latest-match total: <b>{pts(total)}</b> pts",
        "Tap a player below to set captain, vice-captain or remove.",
    ]
    return "\n".join(out)


def fixtures(items: Iterable[Fixture]) -> str:
    items = list(items)
    if not items:
        return "No matches today in the competitions I follow."
    out = ["📅 <b>Today's matches</b>", ""]
    out += [f"{f.kickoff:%H:%M} UTC · {fixture_line(f)}" for f in items]
    return "\n".join(out)


def rules_text(rules: Rules) -> str:
    if isinstance(rules, CricketRules):
        return cricket_rules_text(rules)
    return football_rules_text(rules)


def cricket_rules_text(r: CricketRules) -> str:
    def plus(v: float) -> str:
        return pts(v, signed=True)

    def ladder(items: Sequence[Threshold], unit: str, cumulative: bool) -> str:
        text = ", ".join(f"{t.at} {unit} {plus(t.points)}" for t in items)
        return f"• {text}" + ("" if cumulative else " (highest only)")

    def rates(title: str, rule: RateRule, unit: str) -> list[str]:
        if not rule.bands:
            return []
        rows = [f"• {escape(b.describe())}: {plus(b.points)}" for b in rule.bands]
        exempt = ", ".join(sorted(p.value.replace("_", "-") + "s" for p in rule.exempt))
        note = f"; not for {exempt}" if exempt else ""
        return ["", f"<b>{title}</b> (from {rule.min_balls} {unit}{note})", *rows]

    out = [
        f"📖 <b>{escape(r.name)}</b> (v{escape(r.version)})",
        "",
        f"• Playing XI: {plus(r.playing_xi)}",
        "",
        "<b>Batting</b>",
        f"• Run: {plus(r.run)} · four: {plus(r.four_bonus)} bonus · six: {plus(r.six_bonus)} bonus",
    ]
    if r.milestones:
        out.append(ladder(r.milestones, "runs", r.milestones_cumulative))
    if r.duck:
        exempt = ", ".join(sorted(p.value.replace("_", "-") + "s" for p in r.duck_exempt))
        out.append(f"• Duck: {plus(r.duck)}" + (f" (not for {exempt})" if exempt else ""))
    out += ["", "<b>Bowling</b>", f"• Wicket: {plus(r.wicket)} (run outs excluded)"]
    if r.lbw_bowled_bonus:
        out.append(f"• LBW/bowled bonus: {plus(r.lbw_bowled_bonus)}")
    if r.hauls:
        out.append(ladder(r.hauls, "wickets", r.hauls_cumulative))
    if r.maiden:
        out.append(f"• Maiden over: {plus(r.maiden)}")
    out += ["", "<b>Fielding</b>", f"• Catch: {plus(r.catch)}"]
    if r.catch_bonus:
        out.append(f"• {r.catch_bonus.at} catches: {plus(r.catch_bonus.points)} bonus")
    out += [
        f"• Stumping: {plus(r.stumping)}",
        f"• Run out: {plus(r.run_out_direct)} direct hit, {plus(r.run_out_assisted)} assist",
    ]
    out += rates("Strike rate", r.strike_rate, "balls faced")
    out += rates("Economy rate", r.economy, "balls bowled")
    out += [
        "",
        f"👑 Captain ×{pts(r.multipliers[Role.CAPTAIN])} · "
        f"Vice-captain ×{pts(r.multipliers[Role.VICE_CAPTAIN])}",
    ]
    return "\n".join(out)


def football_rules_text(rules: ScoringRules) -> str:
    def row(label: str, table) -> str:
        vals = {pos: table[pos] for pos in Position if table[pos]}
        if not vals:
            return ""
        if len(set(vals.values())) == 1 and len(vals) == len(Position):
            return f"• {label}: {pts(next(iter(vals.values())), signed=True)}"
        parts = ", ".join(f"{POSITION_ICON[p]} {pts(v, signed=True)}" for p, v in vals.items())
        return f"• {label}: {parts}"

    out = [
        f"📖 <b>{escape(rules.name)}</b> (v{escape(rules.version)})",
        "",
        f"• Starting XI: {pts(rules.starting_xi, signed=True)}",
        f"• Came off the bench: {pts(rules.substitute, signed=True)}",
    ]
    out += [
        r
        for key, label in STAT_LABELS.items()
        if key in rules.per_event and (r := row(label, rules.per_event[key]))
    ]
    cs = row(f"Clean sheet ({rules.clean_sheet_min_minutes}+ min)", rules.clean_sheet_points)
    if cs:
        out.append(cs)
    out += [
        "",
        f"👑 Captain ×{pts(rules.multipliers[Role.CAPTAIN])} · "
        f"Vice-captain ×{pts(rules.multipliers[Role.VICE_CAPTAIN])}",
    ]
    if rules.red_replaces_yellow:
        out.append("A red card cancels a yellow from the same match.")
    return "\n".join(out)
