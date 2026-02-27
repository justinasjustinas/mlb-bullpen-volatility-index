import unittest

from extract import extract_relief_appearances


class ExtractTests(unittest.TestCase):
    def test_extract_relief_appearance_from_minimal_feed(self) -> None:
        feed = {
            "gamePk": 123,
            "gameData": {
                "datetime": {"officialDate": "2025-04-01"},
                "teams": {
                    "home": {"id": 100, "abbreviation": "HOM", "name": "Home"},
                    "away": {"id": 200, "abbreviation": "AWY", "name": "Away"},
                },
            },
            "liveData": {
                "boxscore": {
                    "teams": {
                        "home": {
                            "team": {"id": 100},
                            "players": {
                                "ID1": {
                                    "person": {"id": 1, "fullName": "Starter"},
                                    "stats": {"pitching": {"gamesStarted": 1}},
                                },
                                "ID2": {
                                    "person": {"id": 2, "fullName": "Reliever"},
                                    "stats": {
                                        "pitching": {
                                            "gamesStarted": 0,
                                            "runs": 1,
                                            "inheritedRunners": 2,
                                            "inheritedRunnersScored": 1,
                                            "numberOfPitches": 18,
                                        }
                                    },
                                },
                            },
                        },
                        "away": {"team": {"id": 200}, "players": {}},
                    }
                },
                "plays": {
                    "allPlays": [
                        {
                            "about": {
                                "isTopInning": True,
                                "inning": 8,
                                "homeScore": 3,
                                "awayScore": 2,
                            },
                            "count": {"outs": 1},
                            "matchup": {"pitcher": {"id": 2}},
                            "runners": [],
                        }
                    ]
                },
            },
        }

        apps = extract_relief_appearances(feed)
        self.assertEqual(len(apps), 1)
        ap = apps[0]
        self.assertEqual(ap.team_id, 100)
        self.assertEqual(ap.inning_entered, 8)
        self.assertEqual(ap.outs_on_entry, 1)
        self.assertEqual(ap.score_diff_on_entry, 1)
        self.assertEqual(ap.inherited_runners, 2)
        self.assertEqual(ap.inherited_runners_scored, 1)


if __name__ == "__main__":
    unittest.main()
