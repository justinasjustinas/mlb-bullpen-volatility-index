import unittest
from datetime import date

from mlb_api import MLBApiClient


class MLBApiTests(unittest.TestCase):
    def test_completed_regular_season_filter(self) -> None:
        today = date(2026, 4, 22)

        self.assertTrue(
            MLBApiClient._is_completed_regular_season_game(
                {
                    "gameType": "R",
                    "officialDate": "2026-04-21",
                    "status": {
                        "abstractGameState": "Final",
                        "codedGameState": "F",
                        "detailedState": "Final",
                    },
                },
                today,
            )
        )

        self.assertFalse(
            MLBApiClient._is_completed_regular_season_game(
                {
                    "gameType": "S",
                    "officialDate": "2026-03-20",
                    "status": {
                        "abstractGameState": "Final",
                        "codedGameState": "F",
                        "detailedState": "Final",
                    },
                },
                today,
            )
        )

        self.assertFalse(
            MLBApiClient._is_completed_regular_season_game(
                {
                    "gameType": "R",
                    "officialDate": "2026-09-09",
                    "status": {
                        "abstractGameState": "Preview",
                        "codedGameState": "S",
                        "detailedState": "Scheduled",
                    },
                },
                today,
            )
        )

        self.assertFalse(
            MLBApiClient._is_completed_regular_season_game(
                {
                    "gameType": "R",
                    "officialDate": "2026-04-22",
                    "status": {
                        "abstractGameState": "Live",
                        "codedGameState": "M",
                        "detailedState": "In Progress",
                    },
                },
                today,
            )
        )


if __name__ == "__main__":
    unittest.main()
