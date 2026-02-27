import unittest

from extract import ReliefAppearance, TeamSeasonData
from metrics import TeamMetrics, compute_team_metrics, entry_pressure, finalize_bvi


class MetricsTests(unittest.TestCase):
    def test_entry_pressure_weights(self) -> None:
        ap = ReliefAppearance(
            team_id=1,
            team_abbrev="TST",
            team_name="Test",
            game_pk=1,
            game_date="2025-04-01",
            pitcher_id=11,
            pitcher_name="A",
            inning_entered=9,
            outs_on_entry=0,
            runners_on_entry=2,
            score_diff_on_entry=1,
            runs_allowed=0.0,
            inherited_runners=0,
            inherited_runners_scored=0,
            pitches_thrown=12,
        )
        # 1.4 * 1.4 * 1.3 * 1.2
        self.assertAlmostEqual(entry_pressure(ap), 3.0576, places=4)

    def test_compute_and_finalize_bvi(self) -> None:
        apps_a = [
            ReliefAppearance(1, "AAA", "A", 10, "2025-04-01", 1, "p1", 8, 1, 0, 0, 0, 1, 0, 15),
            ReliefAppearance(1, "AAA", "A", 11, "2025-04-02", 2, "p2", 9, 0, 1, 1, 2, 2, 1, 22),
        ]
        apps_b = [
            ReliefAppearance(2, "BBB", "B", 10, "2025-04-01", 3, "p3", 7, 2, 0, 3, 0, 0, 0, 8),
            ReliefAppearance(2, "BBB", "B", 11, "2025-04-02", 4, "p4", 8, 1, 2, 2, 1, 1, 1, 30),
        ]

        m1 = compute_team_metrics(TeamSeasonData(1, "AAA", "A", apps_a))
        m2 = compute_team_metrics(TeamSeasonData(2, "BBB", "B", apps_b))
        ranked = finalize_bvi([m1, m2])

        self.assertEqual(len(ranked), 2)
        for m in ranked:
            self.assertGreaterEqual(m.bvi, 0)
            self.assertLessEqual(m.bvi, 100)
            self.assertGreaterEqual(m.impact_norm, 0)
            self.assertLessEqual(m.impact_norm, 100)


    def test_bvi_component_weights(self) -> None:
        metrics = [
            TeamMetrics(1, "AAA", "A", 0, 0, 0, 0.0, 0.0, 0.0, 0.0),
            TeamMetrics(2, "BBB", "B", 0, 0, 0, 0.0, 0.0, 0.0, 0.0),
        ]
        metrics[0].impact_volatility = 1.0
        metrics[0].inherited_instability = 10.0
        metrics[0].fatigue_volatility = 1.0

        metrics[1].impact_volatility = 10.0
        metrics[1].inherited_instability = 1.0
        metrics[1].fatigue_volatility = 1.0

        ranked = finalize_bvi(metrics)

        # Teams should tie because impact and inherited components are equally weighted.
        self.assertAlmostEqual(ranked[0].bvi, ranked[1].bvi, places=6)

    def test_inherited_weighting_and_fatigue_cv(self) -> None:
        apps = [
            ReliefAppearance(1, "AAA", "A", 10, "2025-04-01", 1, "p1", 8, 1, 0, 1, 0, 1, 1, 10),
            ReliefAppearance(1, "AAA", "A", 11, "2025-04-02", 2, "p2", 8, 1, 0, 1, 0, 3, 0, 30),
            ReliefAppearance(1, "AAA", "A", 12, "2025-04-03", 3, "p3", 8, 1, 0, 1, 0, 0, 0, 20),
        ]

        metrics = compute_team_metrics(TeamSeasonData(1, "AAA", "A", apps))

        # Weighted inherited-runner instability should be > 0 after smoothing.
        self.assertGreater(metrics.inherited_instability, 0)

        # Fatigue volatility is now coefficient of variation and remains scale-invariant.
        self.assertAlmostEqual(metrics.fatigue_volatility, 0.5, places=4)


if __name__ == "__main__":
    unittest.main()
