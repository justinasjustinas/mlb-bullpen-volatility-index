"""Extraction of bullpen appearances from MLB live feed data."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, Optional


@dataclass
class ReliefAppearance:
    team_id: int
    team_abbrev: str
    team_name: str
    game_pk: int
    game_date: str
    pitcher_id: int
    pitcher_name: str
    inning_entered: int
    outs_on_entry: int
    runners_on_entry: int
    score_diff_on_entry: int
    runs_allowed: float
    inherited_runners: int
    inherited_runners_scored: int
    pitches_thrown: int


@dataclass
class TeamSeasonData:
    team_id: int
    team_abbrev: str
    team_name: str
    appearances: list[ReliefAppearance]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _game_date(feed: Dict[str, Any]) -> str:
    date_raw = feed.get("gameData", {}).get("datetime", {}).get("officialDate")
    if date_raw:
        return date_raw
    date_time = feed.get("gameData", {}).get("datetime", {}).get("dateTime")
    if date_time:
        return datetime.fromisoformat(date_time.replace("Z", "+00:00")).date().isoformat()
    return ""


def _parse_boxscore_pitching(feed: Dict[str, Any]) -> Dict[tuple[int, int], dict[str, Any]]:
    """Map (team_id, pitcher_id) -> single-game pitching stats from boxscore."""
    out: Dict[tuple[int, int], dict[str, Any]] = {}
    box_teams = feed.get("liveData", {}).get("boxscore", {}).get("teams", {})

    for side in ("home", "away"):
        team_blob = box_teams.get(side, {})
        team_id = team_blob.get("team", {}).get("id")
        if not isinstance(team_id, int):
            continue

        players = team_blob.get("players", {})
        for player_key, player in players.items():
            person = player.get("person", {})
            pitcher_id = person.get("id")
            if not isinstance(pitcher_id, int):
                continue
            pitching = player.get("stats", {}).get("pitching", {})
            if not pitching:
                continue

            games_started = _safe_int(pitching.get("gamesStarted"), 0)
            if games_started > 0:
                continue

            out[(team_id, pitcher_id)] = {
                "pitcher_name": person.get("fullName", "Unknown"),
                "runs_allowed": float(pitching.get("runs", 0) or 0),
                "inherited_runners": _safe_int(pitching.get("inheritedRunners"), 0),
                "inherited_runners_scored": _safe_int(
                    pitching.get("inheritedRunnersScored"), 0
                ),
                "pitches_thrown": _safe_int(pitching.get("numberOfPitches") or pitching.get("pitchesThrown"), 0),
            }
    return out


def _count_runners_on_entry(play: dict[str, Any]) -> int:
    starts = set()
    for runner in play.get("runners", []):
        start = runner.get("movement", {}).get("start")
        if start in {"1B", "2B", "3B"}:
            starts.add(start)
    return len(starts)


def _runs_scored_on_play(play: dict[str, Any]) -> int:
    total = 0
    for runner in play.get("runners", []):
        end = runner.get("movement", {}).get("end")
        if end == "score":
            total += 1
    return total


def _extract_entry_state_by_pitcher(feed: Dict[str, Any]) -> Dict[tuple[int, int], dict[str, int]]:
    """Map (team_id, pitcher_id) to first observed game-state on first plate appearance."""
    game_teams = feed.get("gameData", {}).get("teams", {})
    home_id = game_teams.get("home", {}).get("id")
    away_id = game_teams.get("away", {}).get("id")
    if not isinstance(home_id, int) or not isinstance(away_id, int):
        return {}

    entries: Dict[tuple[int, int], dict[str, int]] = {}
    plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    for play in plays:
        matchup = play.get("matchup", {})
        pitcher = matchup.get("pitcher", {})
        pitcher_id = pitcher.get("id")
        if not isinstance(pitcher_id, int):
            continue

        is_top = bool(play.get("about", {}).get("isTopInning", False))
        defensive_team_id = home_id if is_top else away_id
        key = (defensive_team_id, pitcher_id)
        if key in entries:
            continue

        inning = _safe_int(play.get("about", {}).get("inning"), 1)
        outs = _safe_int(play.get("count", {}).get("outs"), 0)
        runners_on = _count_runners_on_entry(play)

        home_after = _safe_int(play.get("about", {}).get("homeScore"), 0)
        away_after = _safe_int(play.get("about", {}).get("awayScore"), 0)
        scored_this_play = _runs_scored_on_play(play)
        if is_top:
            away_before = away_after - scored_this_play
            home_before = home_after
        else:
            home_before = home_after - scored_this_play
            away_before = away_after

        if defensive_team_id == home_id:
            score_diff = home_before - away_before
        else:
            score_diff = away_before - home_before

        entries[key] = {
            "inning": inning,
            "outs": max(0, min(2, outs)),
            "runners_on": max(0, min(3, runners_on)),
            "score_diff": score_diff,
        }

    return entries


def extract_relief_appearances(feed: Dict[str, Any]) -> list[ReliefAppearance]:
    """Extract one record per relief pitcher appearance from a game feed."""
    game_pk = feed.get("gamePk", 0)
    game_date = _game_date(feed)

    game_teams = feed.get("gameData", {}).get("teams", {})
    team_meta: Dict[int, tuple[str, str]] = {}
    for side in ("home", "away"):
        team = game_teams.get(side, {})
        team_id = team.get("id")
        if isinstance(team_id, int):
            team_meta[team_id] = (
                team.get("abbreviation", "UNK"),
                team.get("name", "Unknown"),
            )

    box_map = _parse_boxscore_pitching(feed)
    entry_map = _extract_entry_state_by_pitcher(feed)

    appearances: list[ReliefAppearance] = []
    for (team_id, pitcher_id), box_stats in box_map.items():
        state = entry_map.get(
            (team_id, pitcher_id),
            {"inning": 6, "outs": 1, "runners_on": 0, "score_diff": 0},
        )
        team_abbrev, team_name = team_meta.get(team_id, ("UNK", "Unknown"))
        appearances.append(
            ReliefAppearance(
                team_id=team_id,
                team_abbrev=team_abbrev,
                team_name=team_name,
                game_pk=int(game_pk),
                game_date=game_date,
                pitcher_id=pitcher_id,
                pitcher_name=box_stats["pitcher_name"],
                inning_entered=state["inning"],
                outs_on_entry=state["outs"],
                runners_on_entry=state["runners_on"],
                score_diff_on_entry=state["score_diff"],
                runs_allowed=float(box_stats["runs_allowed"]),
                inherited_runners=int(box_stats["inherited_runners"]),
                inherited_runners_scored=int(box_stats["inherited_runners_scored"]),
                pitches_thrown=int(box_stats["pitches_thrown"]),
            )
        )

    return appearances


def group_by_team(appearances: Iterable[ReliefAppearance]) -> Dict[int, TeamSeasonData]:
    grouped: Dict[int, TeamSeasonData] = {}
    for ap in appearances:
        if ap.team_id not in grouped:
            grouped[ap.team_id] = TeamSeasonData(
                team_id=ap.team_id,
                team_abbrev=ap.team_abbrev,
                team_name=ap.team_name,
                appearances=[],
            )
        grouped[ap.team_id].appearances.append(ap)
    return grouped
