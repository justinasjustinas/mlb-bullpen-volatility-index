import unittest

from extract import ReliefAppearance, TeamSeasonData
from metrics import compute_team_metrics, entry_pressure, finalize_bvi


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


if __name__ == "__main__":
    unittest.main()
