import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

import schedule


NEW_YORK = ZoneInfo("America/New_York")
HOUSE = {"enabled": True, "latitude": 40.7128, "longitude": -74.006, "afterSunset": 20, "end": "23:00"}


class ScheduleTest(unittest.TestCase):
    def test_sunset_is_near_the_known_new_york_times(self):
        summer = schedule.sunset(date(2026, 6, 21), 40.7128, -74.006).astimezone(NEW_YORK)
        winter = schedule.sunset(date(2026, 12, 21), 40.7128, -74.006).astimezone(NEW_YORK)
        self.assertEqual((summer.hour, summer.minute // 10), (20, 3))
        self.assertEqual(winter.hour, 16)
        self.assertLess(abs(winter.minute - 32), 8)

    def test_show_waits_until_dusk_and_stops_at_the_set_time(self):
        evening = schedule.status(HOUSE, datetime(2026, 6, 21, 21, 15, tzinfo=NEW_YORK))
        afternoon = schedule.status(HOUSE, datetime(2026, 6, 21, 15, 0, tzinfo=NEW_YORK))
        late = schedule.status(HOUSE, datetime(2026, 6, 21, 23, 5, tzinfo=NEW_YORK))
        self.assertTrue(evening["on"])
        self.assertFalse(afternoon["on"])
        self.assertFalse(late["on"])
        self.assertIn("PM", evening["starts"])

    def test_a_stop_time_after_midnight_keeps_the_show_on(self):
        saved = {**HOUSE, "end": "01:00"}
        late = schedule.status(saved, datetime(2026, 6, 22, 0, 30, tzinfo=NEW_YORK))
        self.assertTrue(late["on"])

    def test_a_disabled_clock_does_not_change_playback(self):
        result = schedule.status({"enabled": False}, datetime(2026, 6, 21, 12, tzinfo=NEW_YORK))
        self.assertIsNone(result["active"])
        self.assertFalse(result["on"])

    def test_first_update_contains_the_clock(self):
        import re
        import zlib
        import base64
        from pathlib import Path
        import beamloom_player
        import updater
        source = Path(beamloom_player.__file__).read_text(encoding="utf-8")
        payload = re.search(r'ROOT / "schedule.py"\)\.write_bytes\(zlib\.decompress\(base64\.b64decode\("([^"]+)"\)\)\)', source)
        self.assertIsNotNone(payload)
        self.assertEqual(zlib.decompress(base64.b64decode(payload.group(1))), Path(schedule.__file__).read_bytes())
        self.assertIn("player/schedule.py", updater.FILES)

    def test_bad_coordinates_are_ignored(self):
        saved = schedule.clean({"enabled": True, "latitude": 120, "longitude": "west", "end": "25:99", "afterSunset": 900})
        self.assertIsNone(saved["latitude"])
        self.assertEqual(saved["end"], "23:00")
        self.assertEqual(saved["afterSunset"], 20)


if __name__ == "__main__":
    unittest.main()
