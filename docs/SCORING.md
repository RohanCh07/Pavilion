# Scoring rules

Rules live in TOML files under `src/fantasy_bot/scoring/rulesets/`. Point `SCORING_RULESET` at
a bundled name (`dream11_football`, `dream11_cricket`) or at your own file
(`C:\rules\my_league.toml`). Left empty, it follows the sport of `DATA_PROVIDER`.

Data providers only supply raw stats; every point below is computed by the bot.

## Football

```toml
name = "My League"
version = "2"

[appearance]
starting_xi = 4        # played and started
substitute = 2         # came off the bench

[per_event]            # points per occurrence
goals = { goalkeeper = 12, defender = 10, midfielder = 8, forward = 6 }
assists = { default = 8 }            # "default" applies to every position
saves = { goalkeeper = 2 }           # positions not listed get 0
penalties_saved = { goalkeeper = 12 }
penalties_missed = { default = -4 }
own_goals = { default = -6 }
yellow_cards = { default = -2 }
red_cards = { default = -4 }

[clean_sheet]
min_minutes = 60
points = { goalkeeper = 12, defender = 8, midfielder = 4 }

[cards]
red_replaces_yellow = true

[multipliers]
captain = 2.0
vice_captain = 1.5
```

Positions are `goalkeeper`, `defender`, `midfielder`, `forward`; a typo fails at startup.

Countable stats available to `[per_event]`: `goals`, `assists`, `saves`, `penalties_saved`,
`penalties_missed`, `own_goals`, `yellow_cards`, `red_cards`.

## Cricket

A cricket ruleset starts with `sport = "cricket"`. There is one file per match format, and
each match is scored with the rules for its format as reported by the data source:

| Format | File | Used for (CREX labels) |
|---|---|---|
| `t20` | `dream11_cricket.toml` | T20I, T20, T10, The Hundred, and anything unrecognised |
| `odi` | `dream11_cricket_odi.toml` | ODI, One Day, List A, Youth ODI |
| `test` | `dream11_cricket_test.toml` | Test, First Class |

The T20 file is the one `SCORING_RULESET` points at; it links the others:

```toml
format = "t20"

[formats]
odi = "dream11_cricket_odi"   # a bundled name, or a path to your own file
test = "dream11_cricket_test"
```

The values follow Dream11's T20, ODI and Test scoring as best known; check them against the
current Dream11 rules and edit freely. The ODI and Test files have the same sections as the
T20 one below; a Test file simply leaves out `[strike_rate]` and `[economy]`.

```toml
sport = "cricket"
name = "Dream11 Cricket (T20)"
version = "1"

[appearance]
playing_xi = 4

[batting]
run = 1
four_bonus = 4
six_bonus = 6
duck = -2
duck_exempt = ["bowler"]
milestones_cumulative = false     # false: only the highest milestone reached counts
milestones = [{ runs = 25, points = 4 }, { runs = 50, points = 8 },
              { runs = 75, points = 12 }, { runs = 100, points = 16 }]

[bowling]
wicket = 30                       # run outs don't count as the bowler's wicket
lbw_bowled_bonus = 8
maiden = 12
hauls_cumulative = false
hauls = [{ wickets = 3, points = 4 }, { wickets = 4, points = 8 }, { wickets = 5, points = 12 }]

[fielding]
catch = 8
catch_bonus = { catches = 3, points = 4 }
stumping = 12
run_out_direct = 12               # the only fielder involved
run_out_assisted = 6              # each of the last two fielders involved

[strike_rate]
min_balls = 10
exempt = ["bowler"]
bands = [{ above = 170, points = 6 }, { above = 150, max = 170, points = 4 },
         { min = 130, max = 150, points = 2 }, { min = 60, max = 70, points = -2 },
         { min = 50, below = 60, points = -4 }, { below = 50, points = -6 }]

[economy]
min_balls = 12
bands = [{ below = 5, points = 6 }, { min = 5, below = 6, points = 4 },
         { min = 6, max = 7, points = 2 }, { min = 10, max = 11, points = -2 },
         { above = 11, max = 12, points = -4 }, { above = 12, points = -6 }]

[multipliers]
captain = 2.0
vice_captain = 1.5
```

Positions are `batter`, `wicket_keeper`, `all_rounder`, `bowler`. Rate bands take `min`/`max`
(inclusive) and `above`/`below` (strict); the first band that matches wins, and a rate in no
band scores 0. Strike rate is runs x 100 / balls faced; economy is runs conceded x 6 / balls
bowled.

Stats available from the scorecard (`CricketStats`): `in_xi`, `batted`, `out`, `runs`,
`balls_faced`, `fours`, `sixes`, `balls_bowled`, `runs_conceded`, `wickets`, `lbw_bowled`,
`maidens`, `catches`, `stumpings`, `run_outs_direct`, `run_outs_assisted`. Dot balls aren't
available from CREX, so there is no dot-ball rule.

## Adding a new stat

1. Add the field to `PlayerStats` (or `CricketStats`) in `domain.py`.
2. Fill it in the mapper (`providers/api_football_mapper.py` or `providers/crex_parser.py`),
   and the mock if useful.
3. Football: add a label in `STAT_LABELS` (`scoring/engine.py`). Cricket: add a rule and a
   score line in `scoring/cricket.py`. Then add a phrase and icon in `messages.py`.
4. Give it points in the ruleset.

Live alerts pick it up automatically, because they are computed from score-line differences.
