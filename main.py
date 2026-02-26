"""
Bullpen Volatility Index prototype (v1).

Run:
    python main.py --season 2025

Notes:
- Pulls MLB Stats API data for all MLB teams.
- Uses game live feeds to isolate relief appearances and entry-state proxies.
- Prints ranked BVI table from least volatile to most volatile.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from extract import TeamSeasonData, extract_relief_appearances, group_by_team
from metrics import TeamMetrics, compute_team_metrics, finalize_bvi
from mlb_api import MLBApiClient


def _fetch_game_appearances(client: MLBApiClient, game_pk: int) -> list:
    try:
        feed = client.get_live_feed(game_pk)
        return extract_relief_appearances(feed)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN failed game {game_pk}: {exc}")
        return []


def _print_section(title: str, rows: list[TeamMetrics]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    print(
        f"{'Rank':>4} {'Team':<5} {'Team Name':<24} {'BVI':>6} {'ImpN':>7} {'InhN':>7} {'FatN':>7} {'Apps':>6} {'InhApps':>8} {'Days':>6}"
    )
    for rank, m in rows:
        print(
            f"{rank:>4} {m.team_abbrev:<5} {m.team_name:<24} "
            f"{m.bvi:6.2f} {m.impact_norm:7.2f} {m.inherited_norm:7.2f} {m.fatigue_norm:7.2f} "
            f"{m.relief_appearances:6d} {m.inherited_appearances:8d} {m.season_days:6d}"
        )


def build_bvi(season: int, workers: int) -> list[TeamMetrics]:
    client = MLBApiClient()
    teams = client.get_teams(season)
    team_by_id = {t["id"]: t for t in teams}

    game_pks = client.get_schedule_game_pks(season)
    print(f"Loaded {len(teams)} teams, {len(game_pks)} games for {season}.")

    all_apps = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_fetch_game_appearances, client, gpk) for gpk in game_pks]
        for fut in as_completed(futures):
            all_apps.extend(fut.result())

    grouped = group_by_team(all_apps)

    # Ensure all MLB teams appear even if no extracted relief appearances.
    for tid, t in team_by_id.items():
        if tid not in grouped:
            grouped[tid] = TeamSeasonData(
                team_id=tid,
                team_abbrev=t.get("abbreviation", "UNK"),
                team_name=t.get("name", "Unknown"),
                appearances=[],
            )

    metrics = [compute_team_metrics(team_data) for team_data in grouped.values()]
    ranked = finalize_bvi(metrics)
    return ranked


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute MLB Bullpen Volatility Index (BVI).")
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    ranked = build_bvi(season=args.season, workers=args.workers)
    indexed = list(enumerate(ranked, start=1))

    least10 = indexed[:10]
    most10 = indexed[-10:]

    _print_section("Top 10 Least Volatile Bullpens", least10)
    _print_section("Top 10 Most Volatile Bullpens", most10)
    _print_section("Full Ranked List", indexed)

    print("\nSanity checks")
    print("-------------")
    zero_apps = [m.team_abbrev for m in ranked if m.relief_appearances == 0]
    if zero_apps:
        print(f"Teams with zero relief appearances extracted: {', '.join(zero_apps)}")
    else:
        print("All teams have non-zero relief appearances.")


if __name__ == "__main__":
    main()
