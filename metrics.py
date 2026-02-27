"""Bullpen Volatility Index (BVI) metric calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, stdev
from typing import Iterable

from extract import ReliefAppearance, TeamSeasonData


IMPACT_WEIGHT = 0.40
INHERITED_WEIGHT = 0.40
FATIGUE_WEIGHT = 0.20


@dataclass
class TeamMetrics:
    team_id: int
    team_abbrev: str
    team_name: str
    relief_appearances: int
    inherited_appearances: int
    season_days: int
    impact_volatility: float
    inherited_instability: float
    fatigue_volatility: float
    high_usage_share: float
    impact_norm: float = 0.0
    inherited_norm: float = 0.0
    fatigue_norm: float = 0.0
    bvi: float = 0.0


def _inning_weight(inning: int) -> float:
    if inning <= 6:
        return 0.8
    if inning == 7:
        return 1.0
    if inning == 8:
        return 1.2
    if inning == 9:
        return 1.4
    return 1.6


def _close_game_weight(score_diff: int) -> float:
    ad = abs(score_diff)
    if ad <= 1:
        return 1.4
    if ad == 2:
        return 1.2
    if ad == 3:
        return 1.0
    return 0.8


def _runners_weight(runners_on: int) -> float:
    return {0: 1.0, 1: 1.15, 2: 1.3, 3: 1.45}.get(runners_on, 1.0)


def _outs_weight(outs: int) -> float:
    return {0: 1.2, 1: 1.0, 2: 0.9}.get(outs, 1.0)


def entry_pressure(ap: ReliefAppearance) -> float:
    return (
        _inning_weight(ap.inning_entered)
        * _close_game_weight(ap.score_diff_on_entry)
        * _runners_weight(ap.runners_on_entry)
        * _outs_weight(ap.outs_on_entry)
    )


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(stdev(values))


def _weighted_std(values: list[float], weights: list[float]) -> float:
    if len(values) < 2 or len(values) != len(weights):
        return 0.0

    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0

    wmean = sum(v * w for v, w in zip(values, weights)) / total_weight
    variance = sum(w * (v - wmean) ** 2 for v, w in zip(values, weights)) / total_weight
    return math.sqrt(variance)


def _coefficient_of_variation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    if avg <= 0:
        return 0.0
    return _std(values) / avg


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return xs[low]
    frac = pos - low
    return xs[low] * (1 - frac) + xs[high] * frac


def _robust_minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    p5 = _quantile(values, 0.05)
    p95 = _quantile(values, 0.95)
    if p95 <= p5:
        return [50.0 for _ in values]

    out = []
    for v in values:
        clipped = min(max(v, p5), p95)
        out.append((clipped - p5) / (p95 - p5) * 100.0)
    return out


def compute_team_metrics(team_data: TeamSeasonData) -> TeamMetrics:
    apps = team_data.appearances
    n_total = len(apps)

    impacts: list[float] = []
    inherited_rates: list[float] = []
    inherited_weights: list[float] = []
    daily_pitches: dict[str, int] = {}

    for ap in apps:
        pressure = entry_pressure(ap)
        outcome = ap.runs_allowed + ap.inherited_runners_scored
        impacts.append(pressure * outcome)

        if ap.inherited_runners > 0:
            inherited_rates.append(ap.inherited_runners_scored / ap.inherited_runners)
            inherited_weights.append(float(ap.inherited_runners))

        if ap.game_date:
            daily_pitches.setdefault(ap.game_date, 0)
            daily_pitches[ap.game_date] += ap.pitches_thrown

    impact_vol = _std(impacts)

    inherited_std = _weighted_std(inherited_rates, inherited_weights)
    total_inherited_runners = sum(inherited_weights)
    stabilization = math.sqrt(total_inherited_runners / (total_inherited_runners + 30.0))
    inherited_instability = inherited_std * stabilization

    pitch_values = list(daily_pitches.values())
    fatigue_vol = _coefficient_of_variation([float(v) for v in pitch_values])

    if pitch_values:
        q80 = _quantile([float(v) for v in pitch_values], 0.8)
        high_days = sum(1 for v in pitch_values if float(v) > q80)
        high_share = high_days / len(pitch_values)
    else:
        high_share = 0.0

    return TeamMetrics(
        team_id=team_data.team_id,
        team_abbrev=team_data.team_abbrev,
        team_name=team_data.team_name,
        relief_appearances=n_total,
        inherited_appearances=len(inherited_rates),
        season_days=len(daily_pitches),
        impact_volatility=impact_vol,
        inherited_instability=inherited_instability,
        fatigue_volatility=fatigue_vol,
        high_usage_share=high_share,
    )


def finalize_bvi(metrics: list[TeamMetrics]) -> list[TeamMetrics]:
    impacts = [m.impact_volatility for m in metrics]
    inherited = [m.inherited_instability for m in metrics]
    fatigue = [m.fatigue_volatility for m in metrics]

    i_norm = _robust_minmax(impacts)
    h_norm = _robust_minmax(inherited)
    f_norm = _robust_minmax(fatigue)

    for idx, m in enumerate(metrics):
        m.impact_norm = i_norm[idx]
        m.inherited_norm = h_norm[idx]
        m.fatigue_norm = f_norm[idx]
        m.bvi = (
            IMPACT_WEIGHT * m.impact_norm
            + INHERITED_WEIGHT * m.inherited_norm
            + FATIGUE_WEIGHT * m.fatigue_norm
        )

    return sorted(metrics, key=lambda x: x.bvi)
