import unittest

import updater


class UpdateTest(unittest.TestCase):
    def test_a_restart_with_no_time_is_stuck(self):
        self.assertTrue(updater.update_is_stuck({"state": "restarting", "message": "Restarting into release 0.1.7."}, 1_000))
        self.assertFalse(updater.update_is_stuck({"state": "restarting", "at": 950}, 1_000))
        self.assertTrue(updater.update_is_stuck({"state": "downloading", "at": 800}, 1_000))
        self.assertFalse(updater.update_is_stuck({"state": "idle"}, 1_000))


if __name__ == "__main__":
    unittest.main()
