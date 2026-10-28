import datetime
import unittest

from city_incidents import INCIDENTS, active_incident


class CityIncidentTests(unittest.TestCase):
    def test_incident_is_deterministic_within_period(self):
        now = datetime.datetime(2026, 10, 28, 8, tzinfo=datetime.timezone.utc)
        self.assertEqual(active_incident(now), active_incident(now))

    def test_incident_changes_for_other_daypart(self):
        morning = datetime.datetime(2026, 10, 28, 8, tzinfo=datetime.timezone.utc)
        night = datetime.datetime(2026, 10, 28, 23, tzinfo=datetime.timezone.utc)
        self.assertNotEqual(active_incident(morning)["period"], active_incident(night)["period"])

    def test_every_incident_has_rewards_and_story(self):
        for part, incidents in INCIDENTS.items():
            self.assertGreaterEqual(len(incidents), 3)
            for incident in incidents:
                self.assertTrue(incident["story"])
                self.assertGreater(incident["cash"], 0)
                self.assertGreater(incident["xp"], 0)
                self.assertTrue(incident["success"])


if __name__ == "__main__":
    unittest.main()
