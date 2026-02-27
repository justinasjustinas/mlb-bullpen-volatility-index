# Bullpen Volatility Index (BVI) Model (v1)

This prototype computes one **team-level BVI score (0-100)** for each MLB team in a season.

## Data source
- MLB Stats API (`statsapi.mlb.com`) only.
- Team list: `/api/v1/teams?sportId=1&season={season}`
- Schedule: `/api/v1/schedule?sportId=1&season={season}&gameTypes=R,F,D,L,W,S`
- Per-game feed: `/api/v1.1/game/{gamePk}/feed/live`

## Bullpen isolation
- Relief appearances are inferred from game boxscore pitching lines where `gamesStarted == 0`.
- Each relief pitcher appearance in a game becomes one record.

## Component 1: Impact proxy volatility (WPA-ish proxy)
For each relief appearance:
1. `entry_pressure = inning_weight * close_game_weight * runners_on_weight * outs_weight`
   - `inning_weight`: <=6:0.8, 7:1.0, 8:1.2, 9:1.4, extras:1.6
   - `close_game_weight` by `abs(score_diff_on_entry)`: <=1:1.4, 2:1.2, 3:1.0, 4+:0.8
   - `runners_on_weight`: 0:1.0, 1:1.15, 2:1.3, 3:1.45
   - `outs_weight`: 0:1.2, 1:1.0, 2:0.9
2. `appearance_outcome = runs_allowed + inherited_runners_scored`
3. `impact_proxy = entry_pressure * appearance_outcome`

Team component:
- `impact_volatility = sample_stddev(impact_proxy across all relief appearances)`

## Component 2: Inherited runner instability
For relief appearances with inherited runners > 0:
- `inherited_scored_rate = inherited_runners_scored / inherited_runners`

Team component:
- `inherited_instability = weighted_stddev(inherited_scored_rate, weights=inherited_runners) * sqrt(total_inherited_runners / (total_inherited_runners + 30))`

## Component 3: Fatigue stress proxy
Per team day:
- `daily_bullpen_pitches = sum(pitches_thrown by all relievers)`

Team component:
- `fatigue_volatility = sample_stddev(daily_bullpen_pitches) / mean(daily_bullpen_pitches)`
- Also reported: `high_usage_share`, the share of days above team-specific 80th percentile of daily bullpen pitches.

## Normalization and final BVI
Across all teams, for each component:
1. Clip raw values to [5th percentile, 95th percentile].
2. Min-max scale clipped values to [0, 100].

Final composite:
- `BVI = 0.50 * impact_norm + 0.30 * inherited_norm + 0.20 * fatigue_norm`

Interpretation:
- **Lower BVI = more stable bullpen behavior**
- **Higher BVI = more volatile bullpen behavior**

## Known approximation points
- Entry state is inferred from first play in which a reliever appears in the game feed play-by-play.
- Score differential on entry is reconstructed from play score context and runs scored on that first play.
- If entry state is missing, conservative defaults are used.
